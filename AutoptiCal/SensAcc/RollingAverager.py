class RollingAverager:
    from collections import deque

    def __init__(self, window_size):
        self.window_size = window_size
        self.buffer = self.deque(maxlen=window_size)
        self.total = 0

    def update(self, new_sample):
        """
        Updates the total based on the new sample, maintains the buffer size,
        and returns the updated average value.
        """
        if len(self.buffer) == self.window_size:
            self.total -= self.buffer.popleft()  # remove oldest value if buffer is full
        if new_sample != 0:
            self.buffer.append(new_sample)
            self.total += new_sample
        return self.average()

    def average(self):
        """
        Returns the average of the samples in the buffer.
        If no samples are present, returns None.
        """
        count = len(self.buffer)
        if count == 0:
            return -1
        return self.total / count
