# LoL ARAM Helper

英雄联盟大乱斗助手 [[B站教程]](https://www.bilibili.com/video/BV1U341137PF)

## 功能

- 自动选人
- 自动确认
- 获取队友战绩并发送消息
- 保存队伍成员近20场战绩信息

``使用时建议不要关闭客户端``

## 使用方法

1. Release界面直接下载打包好的可执行文件
2. 源码运行（需要有python环境）：
    ```shell
    > git clone https://github.com/Dragon-GCS/LOLHelper.git
    > cd LOLHelper
    > pip install -r requirements.txt
    > python main.pyw
    ```

## 参考资料

- [从零开始写个LOL上等马软件](https://www.bilibili.com/video/BV1A34y117kh)
- [对局先知](https://github.com/real-web-world/hh-lol-prophet)
- [awesome lpl developer tools](https://github.com/CommunityDragon/awesome-league#developer-tools)
- [riot developer docs](https://developer.riotgames.com/docs/lol)
- [lcu api doc](https://lcu.vivide.re/)
- [lcu api swagger doc](https://www.mingweisamuel.com/lcu-schema/tool/)
- [ws event](https://hextechdocs.dev/getting-started-with-the-lcu-websocket/)

## Update log

- v1.1 add: 保存队伍成员战绩开关，用于后续数据分析
- v1.0 自动选人、自动确认、战绩分析
