import bz2
import shutil
import os

# 解压 bz2
input_file = r'D:\下载\phemernrdataset.tar.bz2'
output_dir = r'E:\rumor_detection\data'

print(f"解压: {input_file}")

with bz2.open(input_file, 'rb') as f:
    with open(os.path.join(output_dir, 'phemernrdataset.tar'), 'wb') as out:
        shutil.copyfileobj(f, out)

print("解压完成!")

# 解压 tar
import tarfile
tar_file = os.path.join(output_dir, 'phemernrdataset.tar')
print(f"解压tar: {tar_file}")

with tarfile.open(tar_file, 'r') as tar:
    tar.extractall(output_dir)

print("全部完成!")
