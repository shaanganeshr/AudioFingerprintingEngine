import numpy as np
import heapq

# CIRCULAR QUEUE
class CircularAudioQueue:

    #Buffer for audio frame extraction
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = np.zeros(capacity, dtype=np.float32)
        self.head = 0 
        self.tail = 0  
        self.size = 0

    def push_chunk(self, samples: np.ndarray):
        #Pushes an array of audio samples
        for s in samples:
            self.buffer[self.tail] = s
            self.tail = (self.tail + 1) % self.capacity
            if self.size < self.capacity:
                self.size += 1
            else:
                self.head = (self.head + 1) % self.capacity

    def get_ordered_frame(self) -> np.ndarray:
        #Unrolls the circular buffer from head to tail into a contiguous 1D frame
        if self.head == 0:
            return self.buffer[:self.size].copy()
        return np.concatenate((self.buffer[self.head:], self.buffer[:self.tail]))

    def pop_hop(self, hop_size: int):
        #Advances the read pointer by hop_size in O(1) time.
        advance = min(hop_size, self.size)
        self.head = (self.head + advance) % self.capacity
        self.size -= advance



#DISJOINT SPARSE TABLE (DST)
class DisjointSparseTable:
    #1D Disjoint Sparse Table for Range Maximum Queries
    def __init__(self, arr: np.ndarray):
        self.orig_n = len(arr)
        #Pad array length to next power of 2
        self.levels = max(1, (self.orig_n - 1).bit_length())
        self.n = 1 << self.levels
        self.padded = np.full(self.n, -np.inf, dtype=np.float32)
        self.padded[:self.orig_n] = arr

        #Table[level][i] stores prefix/suffix maxima from the block midpoint
        self.table = np.full((self.levels, self.n), -np.inf, dtype=np.float32)
        self._build()

    def _build(self):
        self.table[0, :] = self.padded
        for level in range(1, self.levels):
            half_len = 1 << level
            block_len = half_len << 1
            for start in range(0, self.n, block_len):
                mid = start + half_len
                end = start + block_len

                # Left half: suffix maxi going backwards from mid - 1 to start
                self.table[level, mid - 1] = self.padded[mid - 1]
                for i in range(mid - 2, start - 1, -1):
                    self.table[level, i] = max(self.table[level, i + 1], self.padded[i])

                # Right half: prefix maxi going forwards from mid to end - 1
                self.table[level, mid] = self.padded[mid]
                for i in range(mid + 1, end):
                    self.table[level, i] = max(self.table[level, i - 1], self.padded[i])

    def query_max(self, L: int, R: int) -> float:
        L = max(0, L)
        R = min(self.orig_n - 1, R)
        if L == R:
            return float(self.padded[L])
        level = (L ^ R).bit_length() - 1
        return float(max(self.table[level, L], self.table[level, R]))

#BOUNDED MIN-HEAP
class BoundedMinHeap:
    #Stores only the K loudest frequency peaks per spectrogram time slice
    def __init__(self, max_k: int = 6):
        self.max_k = max_k
        self.heap = [] 

    def push_peak(self, amp_db: float, time_idx: int, freq_bin: int):
        item = (float(amp_db), int(time_idx), int(freq_bin))
        if len(self.heap) < self.max_k:
            heapq.heappush(self.heap, item)
        elif amp_db > self.heap[0][0]:
            heapq.heapreplace(self.heap, item)

    def get_peaks(self) -> list[tuple[int, int]]:
        return [(t, f) for (_, t, f) in self.heap]

# 2D KD-TREE 
class KDNode:
    __slots__ = ("point", "idx", "left", "right")
    def __init__(self, point, idx, left=None, right=None):
        self.point = point 
        self.idx = idx     
        self.left = left
        self.right = right


class Custom2DKDTree:
    def __init__(self, peaks: np.ndarray):
        indexed_pts = [(peaks[i], i) for i in range(len(peaks))]
        self.root = self._build(indexed_pts, depth=0)

    def _build(self, indexed_pts, depth: int):
        if not indexed_pts:
            return None
        axis = depth % 2
        indexed_pts.sort(key=lambda x: x[0][axis])
        mid = len(indexed_pts) // 2
        return KDNode(
            point=indexed_pts[mid][0],
            idx=indexed_pts[mid][1],
            left=self._build(indexed_pts[:mid], depth + 1),
            right=self._build(indexed_pts[mid + 1:], depth + 1)
        )

    def query_target_box(self, t_min: int, t_max: int, f_min: int, f_max: int) -> list[int]:
        #Returns sorted peak indices that fall strictly inside the range given
        results = []
        self._range_search(self.root, t_min, t_max, f_min, f_max, depth=0, results=results)
        return sorted(results)

    def _range_search(self, node: KDNode, t_min: int, t_max: int, f_min: int, f_max: int, depth: int, results: list):
        if node is None:
            return
        t, f = node.point[0], node.point[1]

        #Check if current node lies inside the target
        if t_min <= t <= t_max and f_min <= f <= f_max:
            results.append(node.idx)

        axis = depth % 2
        val = t if axis == 0 else f
        low = t_min if axis == 0 else f_min
        high = t_max if axis == 0 else f_max

        #Prune subtrees
        if low <= val:
            self._range_search(node.left, t_min, t_max, f_min, f_max, depth + 1, results)
        if val <= high:
            self._range_search(node.right, t_min, t_max, f_min, f_max, depth + 1, results)


#RADIX TREE
class RadixNode:
    __slots__ = ("children", "is_end")
    def __init__(self):
        self.children = {}  
        self.is_end = False


class FingerprintRadixTree:

    #Acts as a fast prefix-tree index to verify if a 30-bit hash exists in DB

    def __init__(self):
        self.root = RadixNode()

    def insert(self, hash_30bit: int):
        node = self.root
        # Traverse 30-bit integer in five 6-bit chunks 
        for shift in (24, 18, 12, 6, 0):
            chunk = (hash_30bit >> shift) & 0x3F
            if chunk not in node.children:
                node.children[chunk] = RadixNode()
            node = node.children[chunk]
        node.is_end = True

    def contains(self, hash_30bit: int) -> bool:
        node = self.root
        for shift in (24, 18, 12, 6, 0):
            chunk = (hash_30bit >> shift) & 0x3F
            if chunk not in node.children:
                return False
            node = node.children[chunk]
        return node.is_end

#ROBIN HOOD HASH TABLE
class RobinHoodHashTable:
    #Tracks Probe Sequence Length (PSL)
    def __init__(self, initial_capacity: int = 16384):
        self.capacity = initial_capacity
        self.size = 0
        self.keys = [None] * self.capacity
        self.values = [None] * self.capacity
        self.psl = [0] * self.capacity 

    def _hash(self, key: int) -> int:
        # Fibonacci multiplicative hashing for 64-bit integer keys
        return ((key * 11400714819323198485) & 0xFFFFFFFFFFFFFFFF) % self.capacity

    def _resize(self):
        old_keys, old_vals = self.keys, self.values
        self.capacity *= 2
        self.size = 0
        self.keys = [None] * self.capacity
        self.values = [None] * self.capacity
        self.psl = [0] * self.capacity

        for k, v_list in zip(old_keys, old_vals):
            if k is not None:
                for item in v_list:
                    self.append_posting(k, item)

    def append_posting(self, key: int, posting: tuple[int, int]):
        if self.size >= self.capacity * 0.7:
            self._resize()

        idx = self._hash(key)
        dist = 0

        # First check if key already exists along the probe path
        curr_idx = idx
        curr_dist = 0
        while self.keys[curr_idx] is not None and curr_dist <= self.psl[curr_idx]:
            if self.keys[curr_idx] == key:
                self.values[curr_idx].append(posting)
                return
            curr_idx = (curr_idx + 1) % self.capacity
            curr_dist += 1

        # Key does not exist then insert new key
        curr_key = key
        curr_val = [posting]
        while True:
            if self.keys[idx] is None:
                self.keys[idx] = curr_key
                self.values[idx] = curr_val
                self.psl[idx] = dist
                self.size += 1
                return

            # Robin Hood rule
            if dist > self.psl[idx]:
                curr_key, self.keys[idx] = self.keys[idx], curr_key
                curr_val, self.values[idx] = self.values[idx], curr_val
                dist, self.psl[idx] = self.psl[idx], dist

            idx = (idx + 1) % self.capacity
            dist += 1

    def get(self, key: int) -> list[tuple[int, int]]:
        idx = self._hash(key)
        dist = 0
        while self.keys[idx] is not None:
            if dist > self.psl[idx]:
                return []
            if self.keys[idx] == key:
                return self.values[idx]
            idx = (idx + 1) % self.capacity
            dist += 1
        return []