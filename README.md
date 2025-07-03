# 使用方法

```shell
pip install requests
python app.py

# 打包exe
pyinstaller --onefile --icon=icon.png --name=飞牛跳转PotPlayer app.py
```

1.nas需要开通smb协议，相关影视的文件夹可见；并确保在文件管理器上访问过一次（用于记录账号密码信息）  
2.视频文件必须是 我的文件（即应用权限添加文件夹那个框左边第一个）下的文件  
不能是 `@appcenter` 这种之类的，必须是用户创建的文件夹，否则smb无法访问到  
3.需要安装谷歌插件，在 `chrome-extensions` 文件夹

## 电视剧使用事项

PotPlayer 需创建一个 fntv 的配置文件，创建步骤如下  
> Pot 选项 > 配置 > 用当前方案创建 > 改配置文件名称为 `fntv`（用脚本播放时会自动切换为该配置）:  
 Pot 选项 > 左上角切换配置为 fntv > 基本 > 相似文件打开策略 > 仅打开选定的文件 > 确定 > 关闭。


创建后，脚本会自动使用此配置，修改后，播放列表就只会显示一个文件了，从播放列表自动跳到下一集，无法回传进度。