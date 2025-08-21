# 浅谈BurpSuite绕过验证码找回密码

---

**URL**: https://www.freebuf.com/articles/web/444354.html

**作者**: 2025-08-14 09:58:20

**发布时间**: 2025-08-14 09:58:20

**爬取时间**: 2025-08-20T17:38:20.190080

---

## 正文

官方公众号企业安全新浪微博

![图片](../images/f43141f724f98ea95118b8af321c69fe.jpg)
FreeBuf.COM网络安全行业门户，每日发布专业的安全资讯、技术剖析。

![FreeBuf+小程序](../images/58489bc90c4e5bff5ef6e4f8a8bafaae.jpg)
FreeBuf+小程序把安全装进口袋

浅谈BurpSuite绕过验证码找回密码

- Web安全

浅谈BurpSuite绕过验证码找回密码
2025-08-14 09:58:20
## 利用BURP插件绕过验证码找回密码

在前篇文章中，我提到过利用Burp找回密码。通常就name和passwd这两个字段，利用Intruder模块即可完成。但是这种方法只适用于简单的程序，对复杂的的比如含有验证码的。就显得力不从心了。本文为你介绍利用BURP插件，对含有验证码的程序如何"找回"密码。

### 原理

还是和之前一样，我们利用burp抓包，用插件来自动识别验证码，然后在爆破模块中调用，实现验证码绕过。

如上，我们利用burp抓包。可以得到对应的验证码字段。

### 下载插件

项目地址：https://github.com/c0ny1/captcha-killer/tags

下载完后，在burp suite中的Extender选项卡中，导入插件。点击Add后，找到你刚才下载的.jar文件，导入即可

### 获取验证码URL

右键对验证码审查元素，获取验证码URL

打开burpsuite，访问这个url，抓取到这个请求验证码的包后，发送到插件去.

这时插件就会接收到你发送过去的数据包，点击获取，能正常显示图片就可以了

### 配置图鉴

captcha-killer本身无法识别验证码，它专注于对各种验证码识别接口的调用。首先去http://www.ttshitu.com/register.html?spm=null中注册帐号 充值一块钱就可以识别500次了

#### 配置captcha-killer

**接口url:http://api.ttshitu.com:80**

构造数据包

```
POST /predict HTTP/1.1Host: api.ttshitu.comUpgrade-Insecure-Requests: 1User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36Accept: application/json;Accept-Encoding: gzip, deflateAccept-Language: zh-CN,zh;q=0.9Cookie: Hm_lvt_d92eb5418ecf5150abbfe0e505020254=1585994993,1586144399; SESSION=5ebf9c31-a424-44f8-8188-62ca56de7bdf; Hm_lpvt_d92eb5418ecf5150abbfe0e505020254=1586****Connection: closeContent-Type: application/json;charset=UTF-8Content-Length: 109{"username":"图鉴用户名","password":"密码","typeid":"3","image":"<@BASE64><@IMG_RAW></@IMG_RAW></@BASE64>"}

```

点击检测，提示如下

```
{"success":true,"code":"0","message":"success","data":{"result":"7603","id":"pIXiWNpmTAi6yw-HagV2nw"}}

```

选择验证码，右键标记为识别结果。

最终效果

### 破解

抓取登录数据包，发送到intruder

设置Attack Type为Pitchfork

设置Payload 1为密码字典

设置Payload 2为插件

最后，破解即可。

### 特别声明

captcha-killer本身无法识别验证码，它专注于对各种验证码识别接口的调用。本文仅限学习和研究，请勿恶意非法攻击，造成法律后果请自负！

# 渗透测试
# web安全
免责声明
1.一般免责声明：
本文所提供的技术信息仅供参考，不构成任何专业建议。读者应根据自身情况谨慎使用且应遵守《中华人民共和国网络安全法》，作者及发布平台不对因使用本文信息而导致的任何直接或间接责任或损失负责。
2. 适用性声明：
文中技术内容可能不适用于所有情况或系统，在实际应用前请充分测试和评估。若因使用不当造成的任何问题，相关方不承担责任。
3. 更新声明：
技术发展迅速，文章内容可能存在滞后性。读者需自行判断信息的时效性，因依据过时内容产生的后果，作者及发布平台不承担责任。
本文为
独立观点，未经授权禁止转载。
如需授权、对文章有疑问或需删除稿件，请联系 FreeBuf
                客服小蜜蜂（微信：freebee1024）
被以下专辑收录，发现更多精彩内容
相关推荐
![图片]
- 0文章数

文章目录
原理
下载插件
获取验证码URL
配置图鉴
- 配置captcha-killer

破解
特别声明
