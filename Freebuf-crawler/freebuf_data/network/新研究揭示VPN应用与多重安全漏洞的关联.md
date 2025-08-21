# 新研究揭示VPN应用与多重安全漏洞的关联

---

**URL**: https://www.freebuf.com/articles/network/444972.html

**作者**: 2025-08-19 18:32:13所属地 上海

**发布时间**: 2025-08-19 18:32:13

**爬取时间**: 2025-08-20T17:40:13.079482

---

## 正文

官方公众号企业安全新浪微博

![图片](../images/f43141f724f98ea95118b8af321c69fe.jpg)
FreeBuf.COM网络安全行业门户，每日发布专业的安全资讯、技术剖析。

![FreeBuf+小程序](../images/58489bc90c4e5bff5ef6e4f8a8bafaae.jpg)
FreeBuf+小程序把安全装进口袋

新研究揭示VPN应用与多重安全漏洞的关联

- 基础安全

新研究揭示VPN应用与多重安全漏洞的关联
2025-08-19 18:32:13
所属地 上海
一项全面的安全分析揭示了影响多个VPN应用程序的严重漏洞，波及超过7亿用户。这些漏洞暴露了关键缺陷，直接威胁到VPN服务承诺保护的隐私与安全。

### 三大家族VPN共享安全隐患

来自亚利桑那州立大学、公民实验室和鲍登学院的网络安全专家研究发现，三个VPN供应商家族不仅存在共同所有权，还共享危险的安全弱点，导致用户通信可能被拦截和解密。调查发现，这些看似独立的VPN提供商存在欺骗行为，故意隐瞒所有权关系，同时共享相同的加密凭证和服务器基础设施。

这些以Innovative Connecting（创新连接）、Autumn Breeze（秋风）和Lemon Clove（柠檬丁香）等名义运营的供应商，共同分发包括Turbo VPN、VPN Proxy Master和Snap VPN等在内的应用程序。

### 硬编码密钥导致流量可解密

研究发现这些应用包含硬编码的Shadowsocks密码，使攻击者能够解密通过其网络传输的所有用户流量。Petsymposium分析师通过对应用程序二进制文件和网络通信的广泛分析，发现安全漏洞源于这些VPN应用处理加密材料时的基本实现错误。

最严重的漏洞涉及直接嵌入应用程序代码中的硬编码对称加密密钥，这些密钥存储在assets/server_offline.ser等文件中，并使用AES-192-ECB加密。当VPN客户端建立连接时，它们使用共享库libopvpnutil.so中实现的本地函数NativeUtils.getLocalCipherKey来确定性生成解密密钥。

技术分析显示，这些应用采用了已弃用的Shadowsocks配置，使用易受攻击的rc4-md5密码套件，缺乏适当的完整性检查，容易遭受解密预言攻击。网络流量分析表明，拥有这些硬编码凭证的攻击者可以实时解密用户通信，Shadowsocks密码在运行时跟踪和内存转储中都可见。

### 感染机制与凭证共享架构

漏洞利用机制的核心在于这些所谓独立VPN提供商之间共享的加密基础设施。每个受影响的应用都包含相同的配置文件和共享库，这些文件在其代码结构中引用了多个VPN应用。

libopvpnutil.so库明确引用了各种VPN包名，包括free.vpn.unblock.proxy.turbovpn、free.vpn.unblock.proxy.vpnmaster和free.vpn.unblock.proxy.vpnmonster，表明这些供应商之间存在协调开发和部署。

当用户连接到这些VPN服务时，应用程序会尝试下载远程配置文件，然后回退到存储在server_offline.ser中的嵌入式硬编码凭证。这种设计使攻击者能够通过在同一网络范围内测试提取的密码来枚举其他VPN服务器，从而有效映射这些欺骗性提供商运营的整个基础设施。共享凭证系统还允许未经授权访问VPN服务，攻击者可以使用从任何受影响应用中提取的Shadowsocks参数建立未经授权的隧道。

**参考来源：**

> New Research Uncovers Connection Between VPN Apps and Multiple Security Vulnerabilities

# 移动安全
# 安全报告
本文为
独立观点，未经授权禁止转载。
如需授权、对文章有疑问或需删除稿件，请联系 FreeBuf
                客服小蜜蜂（微信：freebee1024）
被以下专辑收录，发现更多精彩内容
相关推荐
![图片]
- 0文章数

文章目录
三大家族VPN共享安全隐患
硬编码密钥导致流量可解密
感染机制与凭证共享架构
