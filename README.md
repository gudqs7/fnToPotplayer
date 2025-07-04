# 使用方法

```shell
pip install requests
python app.py

# 打包exe
pyinstaller --onefile --icon=icon.png --name=fn2PotPlayer app.py
```

0.PotPlayer路径为安装版默认路径，即 `C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe`
1.nas需要开通smb协议，相关影视的文件夹可见；并确保在文件管理器上访问过一次（用于记录账号密码信息）  
2.视频文件必须是 我的文件（即应用权限添加文件夹那个框左边第一个）下的文件  
不能是 `@appcenter` 这种之类的，必须是用户创建的文件夹，否则smb无法访问到  
3.需要安装谷歌插件，在 `chrome-extensions` 文件夹或 release 附件

## 电视剧使用事项

PotPlayer 需创建一个 fntv 的配置文件，创建步骤如下  
> Pot 选项 > 配置 > 用当前方案创建 > 改配置文件名称为 `fntv`（用脚本播放时会自动切换为该配置）:  
 Pot 选项 > 左上角切换配置为 fntv > 基本 > 相似文件打开策略 > 仅打开选定的文件 > 确定 > 关闭。

创建后，脚本会自动使用此配置，修改后，播放列表就只会显示一个文件了，从播放列表自动跳到下一集，无法回传进度。  

另外推荐设置收尾处理，否则播放完后需手动Alt+F4
右键播放器界面 > 配置/语言/其他 > 收尾处理 > 选择播放完当前后退出。

## 程序原理

> 首先感谢大佬 `https://github.com/kjtsune/embyToLocalPlayer`  


程序有谷歌插件修改飞牛影视网页，添加按钮，然后发起请求到Python服务端  
Python服务端根据插件的信息访问飞牛影视API（如 `/v/api/v1/item/watched` 用于标记已观看）  
API主要获取视频文件地址，来拼接smb地址，最后用cmd调用PotPlayer播放视频  
同时监控PotPlayer进程关闭情况来获取播放进度，最后将播放进度用API同步到飞牛。  