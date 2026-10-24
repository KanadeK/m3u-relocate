# m3u-relocate 中文说明

把旧 M3U 播放列表的根目录显式映射到新媒体库：先预览、逐条验证本地文件，再生成新的相对路径播放列表。不会移动媒体或修改原播放列表。Python 3.10+，无运行时依赖，不访问网络。

```sh
python -m pip install .
python examples/demo.py demo-output
m3u-relocate old.m3u8 --map 'E:\Old Music=/srv/music' --output portable.m3u8 --format json
m3u-relocate old.m3u8 --map 'E:\Old Music=/srv/music' --output portable.m3u8 --write
```

在 Windows 上将目标换成原生绝对目录，例如 `--map 'E:\Old Music=D:\Music'`。演示中的文件是用于路径检查的非音频占位标记，不声称能够播放。

默认仅预览。即使预览也必须指定 `--output`，因为输出位置决定相对路径。任意本地引用无法解析时，不生成文件；输出已存在也拒绝写入。源播放列表相对路径默认以其所在目录为基准，可通过 `--base` 明确指定。旧目录按路径组件匹配，不会把 `MusicBackup` 错当成 `Music`；重叠映射优先使用最长根目录。

保留注释、顺序及远程 URL；远程 URL 明确标记为未检查且永不请求。支持 Windows 盘符、UNC 和本地 file URI。输出统一 UTF-8、LF、正斜杠相对路径。旧编码可用 `--encoding cp1252` 指定，不自动猜测。

仅验证路径及普通文件存在性，不验证音频解码。不支持 HLS、模糊搜索、复制媒体、修改播放器数据库、盘符相对路径或设备命名空间。默认限制 16 MiB / 20 万条记录。报告含本地路径及可能含令牌的 URL，分享前自行检查。

退出码：0=本地引用均可解析，1=存在条目错误且未写出，2=输入/格式/映射/参数/写入错误。卸载：`python -m pip uninstall m3u-relocate`；按需删除自己生成的演示、导出目录及虚拟环境。MIT 许可。完整边界与安装步骤见 [英文说明](README.md)。
