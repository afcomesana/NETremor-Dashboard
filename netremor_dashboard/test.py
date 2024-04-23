import os
import sys
import imu
import numpy as np
from csvsort import csvsort

filepath = "/home/ging/netremor/data-files/03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4-accelerometer-continuous-1709047462061.csv"

imu.wimu(filepath, "test.imu", 30, 200, "timestamp", ",")

sys.exit(0)

csvsort(filepath, [3], delimiter=",")

with open(filepath, "r") as file:
    gaps = []
    last_timestamp = None
    
    next(file)
    count = 0
    for index, line in enumerate(file):
        timestamp = int(line.split(",")[3])
        
        if last_timestamp is None:
            last_timestamp = timestamp
            continue
        
        gap = timestamp - last_timestamp
        
        if gap > 200:
            count += 1
            
        elif gap > 45:
            print("Interpolation gap: %s (%s)" % (gap, index))
        
        else:
            gaps += [gap]
            # print(gap)

        # if gap > 30 and gap < 200:
        #     print(gap)
        
        

        last_timestamp = timestamp

print("Mean gaps:", np.mean(gaps))
print("Total gaps:", count)