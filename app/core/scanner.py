import os
import xxhash
import asyncio
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor

class FileScanner:
    def __init__(self, chunk_size: int = 1024 * 1024):
        self.chunk_size = chunk_size
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    def get_file_hash(self, file_path: str) -> str:
        """Calculates xxHash64 of a file continuously."""
        try:
            hasher = xxhash.xxh64()
            with open(file_path, 'rb') as f:
                while chunk := f.read(self.chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return None

    async def scan_directory(self, root_path: str) -> Dict[str, List[Dict]]:
        """
        Scans directory in two passes:
        1. Group by Size (Fast)
        2. Group by Hash (Compute Heavy, only for same-size files)
        """
        size_map: Dict[int, List[str]] = {}
        
        # Pass 1: Scan for sizes
        if not os.path.exists(root_path):
            raise ValueError("Directory does not exist")

        for dirpath, _, filenames in os.walk(root_path):
            for f in filenames:
                full_path = os.path.join(dirpath, f)
                try:
                    stats = os.stat(full_path)
                    size = stats.st_size
                    if size > 0: # Ignore empty files
                        if size not in size_map:
                            size_map[size] = []
                        size_map[size].append(full_path)
                except (OSError, PermissionError):
                    continue

        # Filter out unique sizes (cannot be duplicates)
        potential_duplicates = {s: p for s, p in size_map.items() if len(p) > 1}
        
        # Pass 2: Calculate hashes for potential duplicates
        duplicates_by_hash: Dict[str, List[Dict]] = {}
        
        loop = asyncio.get_event_loop()
        
        for size, paths in potential_duplicates.items():
            # Run hashing in thread pool to not block event loop
            tasks = [
                loop.run_in_executor(self.executor, self.get_file_hash, path)
                for path in paths
            ]
            hashes = await asyncio.gather(*tasks)
            
            for path, file_hash in zip(paths, hashes):
                if file_hash:
                    if file_hash not in duplicates_by_hash:
                        duplicates_by_hash[file_hash] = []
                    duplicates_by_hash[file_hash].append({
                        "path": path,
                        "size": size,
                        "hash": file_hash,
                        "name": os.path.basename(path)
                    })

        # Final Filter: Only keep hash groups with >1 file
        return {h: files for h, files in duplicates_by_hash.items() if len(files) > 1}
