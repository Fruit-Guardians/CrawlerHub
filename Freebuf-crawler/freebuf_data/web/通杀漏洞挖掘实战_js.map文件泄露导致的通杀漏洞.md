# 通杀漏洞挖掘实战 | js.map文件泄露导致的通杀漏洞

---

**URL**: https://www.freebuf.com/articles/web/444108.html

**作者**: 2025-08-13 11:56:01所属地 江西省

**发布时间**: 2025-08-13 11:56:01

**爬取时间**: 2025-08-20T17:38:23.276269

---

## 正文

官方公众号企业安全新浪微博

![图片](../images/f43141f724f98ea95118b8af321c69fe.jpg)
FreeBuf.COM网络安全行业门户，每日发布专业的安全资讯、技术剖析。

![FreeBuf+小程序](../images/58489bc90c4e5bff5ef6e4f8a8bafaae.jpg)
FreeBuf+小程序把安全装进口袋

通杀漏洞挖掘实战 | js.map文件泄露导致的通杀漏洞

- Web安全

通杀漏洞挖掘实战 | js.map文件泄露导致的通杀漏洞
2025-08-13 11:56:01
所属地 江西省
### 本文作者：Track-bielang

### 一.简介

**js.map文件是 JavaScript 的Source Map文件，用于存储压缩代码与源代码之间的映射关系。它的主要作用是帮助开发者在调试时，将压缩后的代码还原为可读的源代码，从而快速定位问题。**

平时渗透过程中，会遇到很多的 webpack 打包的站点，webpack 加载的 js 大部分都是变量名混淆的，渗透测试者不好直接查看不同的接口和调试网页。

### Webpack 如何导致 Vue 源码泄露？

**Source Map（.map 文件）泄露原始代码**

- •问题：Webpack 默认生成Source Map（.map 文件），用于调试压缩后的代码。如果**.map**文件被部署到线上，攻击者可以借助工具（如**reverse-sourcemap**）还原出完整的原始代码。

**示例：打包后的**app.js**附带**app.js.map**，攻击者可以：**

```
bashreverse-sourcemap --output-dir ./stolen_src ./dist/app.js.map
```

**直接还原出Vue 组件、API 接口、加密逻辑等。**

**未压缩/未混淆的代码**

- •问题：如果 Webpack 未启用代码压缩（如**TerserPlugin**）或混淆（如**uglifyjs**），打包后的代码可能仍然保留可读的变量名、注释、甚至敏感信息。

**示例：代码里有：**

```
jsconst API_KEY = "sk_live_123456"; // Stripe 生产环境密钥
```

攻击者可以直接在**bundle.js**里搜索关键词（如**API_KEY**、**password**、**secret**）找到敏感数据。

**未正确设置 Webpack 的**mode: 'production'****

- •问题：如果 Webpack 配置未指定**mode: 'production'**，可能会导致：
- •• 未启用代码压缩优化• 包含开发环境调试代码（如 Vue 的**devtools**警告）• 暴露未使用的代码路径（如测试接口、未启用的功能）

**第三方依赖泄露**

- •问题：如果项目中使用了未正确处理的第三方库（如某些 npm 包可能包含敏感信息），它们也会被打包进**bundle.js**。
- •示例：某些库可能在代码里硬编码测试环境的数据库密码、内部 API 地址等。

### 二.工具

#### 1. reverse-sourcemap

**reverse-sourcemap是一个工具，用于从.map文件中逆向还原JavaScript或CSS的源码。**

**1.1. 安装：**

1. 1. 需要先 安装 Node.js 和 npm。（我没写，自己网上找）2. 使用以下命令全局安装 reverse-sourcemap：

```
npm install --global reverse-sourcemap
```

1. 1. 安装完成后，可以通过以下命令检查是否成功：

```
reverse-sourcemap -h
```

**1.2. 工具使用**

在终端中运行以下命令，将源码输出到指定目录：

```
reverse-sourcemap --output-dir sourceCode example.js.map
```

现在就还原出来了。

如果需要递归处理多个 .map 文件，可以添加 -r 参数：

```
reverse-sourcemap -r --output-dir sourceCode
```

#### 2. SourceDetector（插件）

**2.1. 简介**

SourceDetector是一个自动发现.map文件，并帮你下载到本地的一个chrome extension。

**2.2. 项目地址**

```
https://github.com/LuckyZmj/SourceDetector-dist
```

**2.3. 使用**

下载 zip 包之后然后解压，谷歌浏览器添加扩展程序（注意是添加文件中的dist文件夹）

之后你在浏览任何网页时，该插件将自动检测是否有.map文件。其会自动按网站分组显示源码文件，并可点击下载全部或部分源码文件。

### 三.实战复现

访问到一个站点，：

```
http://oa.xxxxx.com:2345/login?redirect=%2F
```

登录口，常规手法无效，无突破。

发现.js.map 文件，反编译发现大量接口：

审计 js 发现好几个接口未授权，但是没什么有价值东西，还是不能突破登录口，于是提指纹找相同系统，运气很好，找到一个测试站点：

```
http://xx.xx.xx.xx:7777/ 
```

使用超管账号登录查看 bp 流量：

发现一个接口通过 token 返回了管理员的账号和密码：

```
/xx/xx/getInfoByToken?token=eyJxx.xx.xx
```

突发奇想将当前系统的接口以及 token 信息带到不同网站去尝试：

结果也返回了当前系统的管理员信息，解密 md5 值：

成功进入系统：

最后提取指纹看看资产多少：

# 漏洞
# 渗透测试
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
本文作者：Track-bielang
一.简介
Webpack 如何导致 Vue 源码泄露？
二.工具
- 1. reverse-sourcemap
- 2. SourceDetector（插件）

三.实战复现
