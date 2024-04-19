import numpy as np
from csvsort import csvsort

filepath = "/home/ging/netremor/data-files/2f73366bc5765cb9bdc1c7f436d03067f200958ff5e7a95635b5577815b62e96-accelerometer.csv"

# csvsort(filepath, [3], delimiter=",")

with open(filepath, "r") as file:
    gaps = []
    last_timestamp = None
    
    next(file)
    count = 0
    for line in file:
        timestamp = int(line.split(",")[3])
        
        if last_timestamp is None:
            last_timestamp = timestamp
            continue
        
        gap = timestamp - last_timestamp
        
        if gap > 200:
            count += 1
        
        elif timestamp < last_timestamp:
            print(gap)
            print("Unordered timestamp")
        
        else:
            gaps += [gap]
            # print(gap)

        # if gap > 30 and gap < 200:
        #     print(gap)
        
        

        last_timestamp = timestamp

print("Mean gaps:", np.mean(gaps))
print("Total gaps:", count)