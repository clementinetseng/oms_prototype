path = r'c:\Users\clementine.tseng_the\Documents\learn\oms_prototype\schemas.py'
with open(path, 'r') as f:
    content = f.read()
content = content.replace('orm_mode = True', 'from_attributes = True')
with open(path, 'w') as f:
    f.write(content)
print("Updated schemas.py")
