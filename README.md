# 开发者

```shell
# 运行
pip install requests
python app.py

# 打包
pip install pyinstaller
pyinstaller --onefile --icon=icon.png --name=fn2PotPlayer app.py
```

# 插件效果

0.支持 L 选择字幕 A 选择音频 （因为直接播放的文件）

1.支持进度回传（仅PotPlayer关闭时回传）

2.支持电影页 `v/movie/*` 和电视剧单集页 `v/tv/episode/*`

3.新增支持电视剧季页面 `/v/tv/season/*` 

4.支持电视剧自动下一集（需配置 相似文件打开策略 和 收尾处理自动退出PotPlayer）

5.仅支持SMB协议


# 使用方法

1.发布页下载 fn2PotPlayer.exe 并保持窗口不关闭  
2.安装谷歌扩展程序：[从谷歌插件商店安装](https://chromewebstore.google.com/detail/%E9%A3%9E%E7%89%9B%E8%B7%B3%E8%BD%ACpotplayer/dfifofodmjbodicabfdibnifpomioajc)  或从附件下载后从开发者模式安装

# 注意事项
0.PotPlayer路径为安装版默认路径，即 `C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe`  
1.nas需要开通smb协议，相关影视的文件夹可见；并确保在文件管理器上访问过一次（用于记录账号密码信息）  
2.视频文件必须是 我的文件（即应用权限添加文件夹那个框左边第一个）下的文件  
不能是系统文件或外部挂载之类的，必须是用户创建的文件夹，一个字就是必须smb能访问到  

## 电视剧使用事项 ！！！

PotPlayer 需创建一个 fntv 的配置文件，创建步骤如下  
> Pot 选项 > 配置 > 用当前方案创建 > 改配置文件名称为 `fntv`（用脚本播放时会自动切换为该配置）:  
 Pot 选项 > 左上角切换配置为 fntv > 基本 > 相似文件打开策略 > 仅打开选定的文件 > 确定 > 关闭。

创建后，脚本会自动使用此配置，修改后，播放列表就只会显示一个文件了，如果是正常从播放列表自动跳到下一集，将无法回传进度。  

另外推荐设置收尾处理，否则播放完后需手动Alt+F4  
右键播放器界面 > 配置/语言/其他 > 收尾处理 > 选择播放完当前后退出。

# 程序原理

> 首先感谢大佬 `https://github.com/kjtsune/embyToLocalPlayer`  


程序有谷歌插件修改飞牛影视网页，添加按钮，然后发起请求到Python服务端  
Python服务端根据插件的信息访问飞牛影视API（如 `/v/api/v1/item/watched` 用于标记已观看）  
API主要获取视频文件地址，来拼接smb地址，最后用cmd调用PotPlayer播放视频  
同时监控PotPlayer进程关闭情况来获取播放进度，最后将播放进度用API同步到飞牛。  
