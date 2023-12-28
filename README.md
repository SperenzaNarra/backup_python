# 简易备份脚本

## 纸面说明

```
usage: backup.py [-h] [-f PATH] [-n PATH NAME] [--force] [--dateless]
                 [--preview]
                 save

positional arguments:
  save          储存备份地址

optional arguments:
  -h, --help    show this help message and exit
  -f PATH       快速备份
  -n PATH NAME  重命名备份
  --force       全局，忽略配置文件
  --dateless    全局，不带日期命名
  --preview     全局，不备份，只显示过程
```

## 快速备份

格式为

```bash
python backup.py [储存备份地址] -f [地址1] -f [地址2] ...
```

例子：如果有一个文件夹格式如下
```
backup.py
folder
├── file1.txt
├── file2.txt
└── file3.txt
```
而我输入指令
```bash
python backup.py backup -f folder
```

第一次它会生成配置文件
<pre><code>
backup.py
<b>backup
└── cache
    └── folder.json</b>
folder
├── file1.txt
├── file2.txt
└── file3.txt
</code></pre>
内容为
```json
{
    "allowlist": [],
    "denylist": [
        ".zip",
        "__pycache__", 
        ".vscode"
    ],
    "auto_clean": true
}
```
设置好白名单和黑名单之后再跑一次 `python backup.py backup -f folder`

它就会在 `backup` 文件夹中生成 `2023-12-20-folder.zip`

<pre><code>
backup.py
<b>backup
├── cache
│   └── folder.json
└── 2023-12-20-folder.zip</b>
folder
├── file1.txt
├── file2.txt
└── file3.txt
</code></pre>

## 重命名备份

格式为

```bash
python backup.py [储存备份地址] -n [地址1] [名称1] -n [地址2] [名称2] ...
```

例子：如果有一个文件夹格式如下
```
backup.py
folder
├── file1.txt
├── file2.txt
└── file3.txt
```
而我输入指令
```bash
python backup.py backup -n folder myfolder
```

第一次它会生成配置文件
<pre><code>
backup.py
<b>backup
└── cache
    └── myfolder.json</b>
folder
├── file1.txt
├── file2.txt
└── file3.txt
</code></pre>
内容为
```json
{
    "allowlist": [],
    "denylist": [
        ".zip",
        "__pycache__", 
        ".vscode"
    ],
    "auto_clean": true
}
```
设置好白名单和黑名单之后再跑一次 `python backup.py backup -f folder`

它就会在 `backup` 文件夹中生成 `2023-12-20-folder.zip`

<pre><code>
backup.py
<b>backup
├── cache
│   └── myfolder.json
└── 2023-12-20-myfolder.zip</b>
folder
├── file1.txt
├── file2.txt
└── file3.txt
</code></pre>

## 自动清理

在配置文件中会有一个参数

```json
"auto_clean": true
```

其作用为：

- 检测所有非本月的同名字文档
- 保留每个月最后一次存档，其余删除

注意：这个功能无法与 dateless 一起使用，因为 dateless 操作是直接覆盖原存档。