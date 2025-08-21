# Kubernetes ：k8s一主两从集群搭建—实现全纪录

---

**URL**: https://www.freebuf.com/articles/container/418863.html

**作者**: 2025-03-26 14:14:04所属地 上海

**发布时间**: 2025-03-26 14:14:04

**爬取时间**: 2025-08-21T09:06:20.899670

---

## 正文

官方公众号企业安全新浪微博

![图片](../images/f43141f724f98ea95118b8af321c69fe.jpg)
FreeBuf.COM网络安全行业门户，每日发布专业的安全资讯、技术剖析。

![FreeBuf+小程序](../images/58489bc90c4e5bff5ef6e4f8a8bafaae.jpg)
FreeBuf+小程序把安全装进口袋

Kubernetes ：k8s一主两从集群搭建—实现全纪录

- 云安全

Kubernetes ：k8s一主两从集群搭建—实现全纪录
2025-03-26 14:14:04
所属地 上海
![图片](../images/b9059b82f9f584c38d557848f19ae621.png)
本文由
创作，已纳入
「FreeBuf原创奖励计划」
，未授权禁止转载
### 一、基本概念

Kubernetes（通常简称为K8s）是一个开源的容器编排引擎，用于自动化部署、扩展和管理容器化应用程序。它最初由Google开发，并于2014年开源。Kubernetes可以在多种基础设施上运行，包括公有云、私有云和混合云环境。以下是Kubernetes的一些基本概念和入门需要了解的内容：

1. 容器化：Kubernetes建立在容器化的基础上，容器是一种轻量级的、可移植的、自包含的软件单元，它们包含了应用程序的所有依赖项和代码，并且可以在任何支持容器的环境中运行。
2. Pods（Pod）： Pod是Kubernetes中最小的可部署单元，它可以包含一个或多个容器。Pod提供了共享网络和存储资源的环境，这些资源可以在Pod中的容器之间共享。通常情况下，一个Pod中只包含一个主容器，其他辅助容器用于辅助任务，如日志收集、监控等。
3. 服务（Service）： 服务用于将一组相同功能的Pod公开为一个网络服务。服务可以提供负载均衡、服务发现和路由功能，使得应用程序能够以统一的方式访问多个Pod。
4. 控制器（Controller）：控制器用于管理Pod的生命周期，确保在集群中始终运行指定数量的Pod副本。常见的控制器包括ReplicaSet、Deployment和StatefulSet等。
5. 标签（Label）和选择器（Selector）： 标签是键值对，用于标识Kubernetes对象（如Pod、Service等），选择器用于根据标签选择和过滤对象。
6. 命名空间（Namespace）： 命名空间用于对Kubernetes资源进行逻辑分组和隔离，不同命名空间中的资源彼此隔离，可以帮助组织和管理多租户环境。
7. 存储卷（Volume）：存储卷是Kubernetes中的持久化存储解决方案，用于在Pod之间共享数据，并且可以在Pod重启时保留数据。

在实际项目中，Kubernetes通常用于以下方面：

- 容器编排和调度： Kubernetes可以自动管理容器的部署、扩展和调度，确保应用程序在集群中高可用和高效运行。
- 持续交付和持续集成： Kubernetes提供了灵活的部署策略和自动化工具，可以实现持续集成和持续交付（CI/CD），帮助开发团队快速、安全地交付代码。
- 微服务架构： Kubernetes提供了丰富的服务发现、负载均衡和路由功能，可以支持复杂的微服务架构，将大型应用程序拆分成多个独立的服务单元进行部署和管理。
- 自动伸缩：Kubernetes可以根据应用程序的负载情况自动扩展和收缩Pod副本数量，以满足动态变化的需求，提高资源利用率和系统的可伸缩性。
- 故障恢复和高可用性： Kubernetes具有自动故障检测和恢复机制，可以在节点故障或Pod失败时自动重新调度和恢复应用程序，保证应用程序的高可用性和可靠性。

### 二、组件介绍

#### 主要组件

kubelet：

- kubelet 是运行在每个 Kubernetes 集群节点上的代理。它负责管理该节点上的容器和 Pod 生命周期。具体来说，kubelet 接收来自 API Server 的 Pod 规范，确保 Pod 中的容器处于运行状态，并根据需要拉取容器镜像。它还监视 Pod 和容器的健康状态，并在需要时重新启动它们。kubelet 通过与容器运行时（如 Docker、containerd 等）进行通信来执行这些任务。

kubeadm：

- kubeadm 是用于初始化 Kubernetes 集群的命令行工具。它简化了 Kubernetes 集群的部署过程，使得用户可以快速地搭建一个功能完整的 Kubernetes 集群。通过 kubeadm，可以轻松地在一组物理或虚拟机上启动一个新的 Kubernetes 集群，包括 Master 节点和 Worker 节点的初始化。kubeadm 还提供了用于入现有集群的命令，以及用于管理集群配置的功能。

kubectl：

- kubectl 是 Kubernetes 的命令行工具，用于与 Kubernetes 集群进行交互。通过 kubectl，用户可以执行各种操作，包括创建、查看、更新和删除 Kubernetes 资源（如 Pod、Service、Deployment 等）。kubectl 提供了一个强大而灵活的命令行界面，允许用户轻松地管理他们的 Kubernetes 集群。kubectl 通过与 Kubernetes API Server 进行通信来执行这些操作。

kubelet 负责节点上的容器和 Pod 的管理，kubeadm 简化了集群的初始化过程，而 kubectl 则是用户与 Kubernetes 集群进行交互的主要工具。

#### 其他组件

kube-apiserver：

- Kubernetes API Server 是整个 Kubernetes 集群的入口点。它公开了 Kubernetes API，允许用户和其他组件与集群进行交互。

etcd：

- etcd 是 Kubernetes 集群的分布式键值存储系统，用于存储集群的所有配置数据和状态信息。

kube-scheduler：

- Kubernetes Scheduler 负责监视新创建的 Pod，并根据预定义的调度策略将它们分配给集群中的节点。

kube-controller-manager：

- Kubernetes Controller Manager 包含了一组控制器，负责监控集群中的各种资源（如 Pod、Service、Volume 等），并确保它们的状态符合预期。

kubelet：

- Kubernetes Kubelet 是运行在每个集群节点上的代理，负责管理节点上的容器和 Pod 的生命周期，并与其他组件进行通信。

kube-proxy：

- Kubernetes Proxy 是负责为 Pod 提供网络代理和负载均衡功能的组件，它通过设置 iptables 规则或者其他技术来实现 Pod 之间的网络通信。

Container Runtime：

- 容器运行时是负责管理和运行容器的软件，如 Docker、containerd、CRI-O 等。

Networking Plugins：

- 网络插件是 Kubernetes 集群中用于实现 Pod 网络通信的组件，常见的网络插件包括 Calico、Flannel、Cilium 等。

Storage Plugins：

- 存储插件是 Kubernetes 集群中用于管理持久化存储的组件，常见的存储插件包括 CSI（Container Storage Interface）插件等。

DNS Add-on：

- DNS Add-on 提供了在 Kubernetes 集群中进行服务发现和 DNS 解析的功能，通常使用 CoreDNS 或 kube-dns 实现。

Ingress Controller：

- Ingress Controller 是用于将外部流量路由到 Kubernetes 集群内部服务的组件，常见的 Ingress Controller 包括 Nginx Ingress Controller、Traefik、HAProxy 等。

Dashboard：

- Kubernetes Dashboard 是一个 Web 用户界面，用于管理和监控 Kubernetes 集群中的各种资源和操作。

Cluster Autoscaler：

- Cluster Autoscaler 是用于自动调整 Kubernetes 集群规模的组件，根据负载和资源需求自动增加或减少集群中的节点。

### 三、前期准备

因为主要是为项目架构学习k8s，不是学习云安全相关，所有全部过程都手工搭建，如果不为了学习Github上有很多相关一键运行的脚本可以更便捷。

搭建环境为三台虚拟机，Centos7系统。

#### 1、安装 Docker

但需注意kubernets自1.24.0 后，就不再使用docker.shim，替换采用containerd作为容器运行时端点。

下载的kubelet、kubeadm、kubectl的版本大于1.24.0的话，初始化将会报错。

| # 1. 安装必要的依赖
sudo yum install -y yum-utils device-mapper-persistent-data lvm2

# 2. 设置 Docker 的稳定版仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 3. 安装 Docker
sudo yum install docker-ce

# 4. 启动 Docker 服务
sudo systemctl start docker

# 5. 设置 Docker 开机自启
sudo systemctl enable docker

# 6. 验证 Docker 是否安装成功
docker --version |
| --- |

#### 2、关闭防火墙

| sudo systemctl status firewalld
sudo systemctl stop firewalld
sudo systemctl disable firewalld |
| --- |

不关闭，初始化会报错。

#### 3、关闭交换内存

| sudo systemctl status firewalld
sudo systemctl stop firewalld
sudo systemctl disable firewalld
// 关闭交换内存
sudo swapon --show
// 临时禁用Swap
sudo swapoff -a
// 永久禁用swap
sed -i 's/.*swap.*/#&/' /etc/fstab |
| --- |

不关闭，初始化会报错。

#### 4、禁用SELinux

kubelet挂载目录时会受SELinux影响，不关闭，初始化会报错Permission denied。

| // 查看状态
sestatus
// 临时禁用
setenforce 0
// 永久禁用
sed -i 's/enforcing/disabled/' /etc/selinux/config |
| --- |

#### 5、修改cgroups

linux中的ubuntu、debian、centos7使用的是systemd初始化系统，systemd有自己的cgroup管理器，容器运行时和kubelet使用的是另一个cgroup管理器，也就是说linux系统的cgroup管理和kubelet的cgroup管理器是两个不一样，系统中存在两种资源分配视图。当系统资源（如cpu、内存等）不足时，操作系统的进程会不稳定。

| vi /etc/docker/daemon.json

{
    "exec-opts": [
        "native.cgroupdriver=systemd"
    ],
    "registry-mirrors": [
        "https://vj4iipoo.mirror.aliyuncs.com"
    ]
}

systemctl restart docker
sudo systemctl daemon-reload

systemctl restart kubelet |
| --- |

#### 6. 组件安装（kubelet、kubectl、kubeadm）

| # 下载k8s软件包仓库的公共签名秘钥
sudo rpm --import https://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg
# 添加 Kubernetes 的 YUM 仓库
sudo tee /etc/yum.repos.d/kubernetes.repo <<EOF
[kubernetes]
name=Kubernetes
baseurl=https://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg https://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg
EOF

# 更新 YUM 包列表
sudo yum update

# 查看可用版本
sudo yum list kubelet kubectl kubeadm --showduplicates | grep '1.23.8-0'

# 安装指定版本
sudo yum install -y kubelet-1.23.8-0 kubectl-1.23.8-0 kubeadm-1.23.8-0

# 标记软件包为保留状态
sudo yum install -y yum-plugin-versionlock
sudo yum versionlock kubelet kubectl kubeadm
# 设置开机自启
systemctl enable --now kubelet
# 查看kubelet状态
systemctl status kubelet
kubectl version
# 验证kubeadm版本
yum info kubeadm |
| --- |

#### 7. 克隆出worker机器

修改主机名称，用以分辨

| hostnamectl set-hostname K8S-MASTER
hostnamectl set-hostname K8S-WORKER1
hostnamectl set-hostname K8S-WORKER2

cat /etc/hostname |
| --- |

### 四、创建集群

#### 1. 初始化（master）

执行kubeadm初始化命令，注意检查版本同步。

| kubeadm init \
  --apiserver-advertise-address=192.168.136.128 \
  --image-repository registry.aliyuncs.com/google_containers \
  --kubernetes-version v1.23.8 \
  --service-cidr=10.96.0.0/12 \
  --pod-network-cidr=10.244.0.0/16 \
  --ignore-preflight-errors=Swap |
| --- |

初始化后输出如下：

| Your Kubernetes control-plane has initialized successfully!

To start using your cluster, you need to run the following as a regular user:

  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config

Alternatively, if you are the root user, you can run:

  export KUBECONFIG=/etc/kubernetes/admin.conf
配置.bash_profile
You should now deploy a pod network to the cluster.
Run "kubectl appl重启网络后，可以重新启动服务，稍等一会后各节点状态正常

y -f [podnetwork].yaml" with one of the options listed at:
  https://kubernetes.io/docs/concepts/cluster-administration/addons/

Then you can join any number of worker nodes by running the following on each as root:  kubeadm join 192.168.136.128:6443 --token mkhl56.41yk10dd5544u46b \
    --discovery-token-ca-cert-hash sha256:846b117292556d4b21ff14b28061826269c816fcd70e6a7560268aabf38ee422 |
| --- |

想要别的节点加入集群就执行红框里的kubeadm join命令就行。

#### 2.配置.kube

根据初始化完成后输出信息的命令进行操作如下

| # 创建.kube文件夹
sudo mkdir -p $HOME/.kube

# 将admin.conf文件内容复制到.kube的config文件中
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config

# 将文件的所有权限从文件所有者修改到到所有者所在的组的其他用户（user->group）
sudo chown $(id -u):$(id -g) $HOME/.kube/config |
| --- |

#### 3.配置.bash_profile

| # 编辑文件
vim /root/.bash_profile

# 将以下内容加入
export KUBECONFIG=/etc/kubernetes/admin.conf

参数详情：
export KUBECONFIG=/etc/kubernetes/admin.conf
超级用户变量配置

# 激活.bash_profile
source /root/.bash_profile |
| --- |

#### 4. 配置网络

部署容器网络，CNI网络插件(在Master上执行，)，这里使用Flannel实现。著名的CNI网络插件有flannel、calico、canal和kube-router等，简单易用的实现是为CoreOS提供的flannel项目。

##### 4.1 kube-flannel.yml

下载kube-flannel.yml

| wget https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml |
| --- |

下载不了自己访问页面把内容拿下来新建文件

| ---
kind: Namespace
apiVersion: v1
metadata:
  name: kube-flannel
  labels:
    k8s-app: flannel
    pod-security.kubernetes.io/enforce: privileged
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  labels:
    k8s-app: flannel
  name: flannel
rules:
- apiGroups:
  - ""
  resources:
  - pods
  verbs:
  - get
- apiGroups:
  - ""
  resources:
  - nodes
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ""
  resources:
  - nodes/status
  verbs:
  - patch
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  labels:
    k8s-app: flannel
  name: flannel
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: flannel
subjects:
- kind: ServiceAccount
  name: flannel
  namespace: kube-flannel
---
apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    k8s-app: flannel
  name: flannel
  namespace: kube-flannel
---
kind: ConfigMap
apiVersion: v1
metadata:
  name: kube-flannel-cfg
  namespace: kube-flannel
  labels:
    tier: node
    k8s-app: flannel
    app: flannel
data:
  cni-conf.json: |
    {
      "name": "cbr0",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "flannel",
          "delegate": {
            "hairpinMode": true,
            "isDefaultGateway": true
          }
        },
        {
          "type": "portmap",
          "capabilities": {
            "portMappings": true
          }
        }
      ]
    }
  net-conf.json: |
    {
      "Network": "10.244.0.0/16",
      "EnableNFTables": false,
      "Backend": {
        "Type": "vxlan"
      }
    }
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kube-flannel-ds
  namespace: kube-flannel
  labels:
    tier: node
    app: flannel
    k8s-app: flannel
spec:
  selector:
    matchLabels:
      app: flannel
  template:
    metadata:
      labels:
        tier: node
        app: flannel
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/os
                operator: In
                values:
                - linux
      hostNetwork: true
      priorityClassName: system-node-critical
      tolerations:
      - operator: Exists
        effect: NoSchedule
      serviceAccountName: flannel
      initContainers:
      - name: install-cni-plugin
        image: docker.io/flannel/flannel-cni-plugin:v1.4.1-flannel1
        command:
        - cp
        args:
        - -f
        - /flannel
        - /opt/cni/bin/flannel
        volumeMounts:
        - name: cni-plugin
          mountPath: /opt/cni/bin
      - name: install-cni
        image: docker.io/flannel/flannel:v0.25.2
        command:
        - cp
        args:
        - -f
        - /etc/kube-flannel/cni-conf.json
        - /etc/cni/net.d/10-flannel.conflist
        volumeMounts:
        - name: cni
          mountPath: /etc/cni/net.d
        - name: flannel-cfg
          mountPath: /etc/kube-flannel/
      containers:
      - name: kube-flannel
        image: docker.io/flannel/flannel:v0.25.2
        command:
        - /opt/bin/flanneld
        args:
        - --ip-masq
        - --kube-subnet-mgr
        resources:
          requests:
            cpu: "100m"
            memory: "50Mi"
        securityContext:
          privileged: false
          capabilities:
            add: ["NET_ADMIN", "NET_RAW"]
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: EVENT_QUEUE_DEPTH
          value: "5000"
        volumeMounts:
        - name: run
          mountPath: /run/flannel
        - name: flannel-cfg
          mountPath: /etc/kube-flannel/
        - name: xtables-lock
          mountPath: /run/xtables.lock
      volumes:
      - name: run
        hostPath:
          path: /run/flannel
      - name: cni-plugin
        hostPath:
          path: /opt/cni/bin
      - name: cni
        hostPath:
          path: /etc/cni/net.d
      - name: flannel-cfg
        configMap:
          name: kube-flannel-cfg
      - name: xtables-lock
        hostPath:
          path: /run/xtables.lock
          type: FileOrCreate |
| --- |

##### 4.2 网段确认

查看配置文件kube-flannel.yml中net-config.json部分的参数，确保Newwork参数的网段值与执行kubeadm init 输入的网段一致。

| net-conf.json: |   
	{
      "Network": "10.244.0.0/16",
      "EnableNFTables": false,
      "Backend": {
        "Type": "vxlan"
      }
    } |
| --- |

##### 4.3 部署flannel

部署命令（如果部署的时候卡在pull镜像的时候，可以手动用docker将镜像拉取下来）：

| kubectl apply -f kube-flannel.yml |
| --- |

##### 4.4 查看kube-flannel服务状态

确保flannel对应的pod状态为Running才可正常使用。查看所有pod状态，其中包含kube-flannel

| kubectl get pod --all-namespaces |
| --- |

确保所有容器正常运行，即Running状态。

这步可能出现很多问题，如果有容器没正常启动，可以查看相关日志，然后搜索相关解决方法，直至全部Running状态，注意可能会有延迟。

**4.5 集群节点查看**

| kubectl get nodes |
| --- |

**4.6 重新配置网络后报错**

因为第一次配置过程中出现一些问题，有重置ip后二次搭建，其中遇到获取所有pad状态时报错

重启网络后，可以重新启动服务，稍等一会后各节点状态正常

### 五、节点加入集群（k8s-worker1、k8s-worker2）

#### 1. 加入集群命令获取（主节点）

注：此命令需在master主节点中执行，token参数有效期24小时，过期则不可用请重新获取如果忘记保存命令或者token过期，可通过以下命令重新生成加入集群的命令

| kubeadm token create --print-join-command

[root@k8s-master as]# kubeadm token create --print-join-command kubeadm join 192.168.129.152:6443 --token gn1i5e.8n39ulkor9xvxirt --discovery-token-ca-cert-hash sha256:6b24c53e0dc1dacdf68ca19952d42094ba8cf3e0fd84f25f7780b98afdbe3607 |
| --- |

每次获取的命令中token会变，但sha不会变

#### 2. 加入集群（子节点）

| [root@localhost kubernetes]# kubeadm join 192.168.129.152:6443 --token gn1i5e.8n39ulkor9xvxirt --discovery-token-ca-cert-hash sha256:6b24c53e0dc1dacdf68ca19952d42094ba8cf3e0fd84f25f7780b98afdbe3607
[preflight] Running pre-flight checks
    [WARNING SystemVerification]: this Docker version is not on the list of validated versions: 26.0.1. Latest validated version: 20.10
[preflight] Reading configuration from the cluster...
[preflight] FYI: You can look at this config file with 'kubectl -n kube-system get cm kubeadm-config -o yaml'
[kubelet-start] Writing kubelet configuration to file "/var/lib/kubelet/config.yaml"
[kubelet-start] Writing kubelet environment file with flags to file "/var/lib/kubelet/kubeadm-flags.env"
[kubelet-start] Starting the kubelet
[kubelet-start] Waiting for the kubelet to perform the TLS Bootstrap...

This node has joined the cluster:
* Certificate signing request was sent to apiserver and a response was received.
* The Kubelet was informed of the new secure connection details.

Run 'kubectl get nodes' on the control-plane to see this node join the cluster.

[root@localhost kubernetes]# |
| --- |

#### 3. 查看集群节点（主节点）

| kubectl get nodes |
| --- |

#### 4、子节点中使用kubectl命令

此时在主节点中kubectl相关命令可正常使用，但在从节点中使用kubectl会报端口问题，如下原因是从节点中没有admin.conf文件，此文件授权kubectl命令的使用，而该文件只有初始化时在主节点中生成了，从节点中并无，故需要将其复制到从节点并配置环境变量使之生效即可。

**4.1 查看文件（主节点）**

在主节点中查看admin.conf文件

| ls /etc/kubernetes/ |
| --- |

**4.2 复制文件（主节点）**

在主节点中执行命令，将admin.conf文件复制到从节点相同目录下

| sudo scp /etc/kubernetes/admin.conf root@k8s-worker1:/etc/kubernetes/ |
| --- |

k8s-worker2执行相同操作

**4.3 工作节点查看（子节点）**

到工作节点中查看文件是否已存在

| ls /etc/kubernetes |
| --- |

k8s-worker1中已存在admin.confk8s-worker2中已存在admin.conf

**4.4 配置环境变量（子节点）**

到工作节点中配置环境变量，使admin.conf文件生效，以下命令k8s-worker1和k8s-worker2都执行一遍

| sudo vim /etc/profile |
| --- |

将以下内容复制粘贴进去

| export KUBECONFIG=/etc/kubernetes/admin.conf |
| --- |

执行命令使环境变量生效

| source /etc/profile |
| --- |

**4.5 再次查看集群节点（子节点）**

在从节点中使用kubectl命令查看集群节点

| kubectl get nodes |
| --- |

k8s-worker1可用k8s-worker2可用

至此，集群搭建已完成，成功加入两个节点，且状态正确。

### 六、Kubernetes安装面板

#### 1 安装 dashboard

**1.1 版本对应**

前文我安装的k8s是1.23.0版本，可以访问https://github.com/kubernetes/dashboard/releases?page=4查看兼容的面板版本

| kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.5.1/aio/deploy/recommended.yaml |
| --- |

**1.2 本地安装**

如果安装失败，可通过创建文件来实现本地加载安装

| # Copyright 2017 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

apiVersion: v1
kind: Namespace
metadata:
  name: kubernetes-dashboard

---

apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kubernetes-dashboard

---

kind: Service
apiVersion: v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kubernetes-dashboard
spec:
  ports:
    - port: 443
      targetPort: 8443
  selector:
    k8s-app: kubernetes-dashboard

---

apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-certs
  namespace: kubernetes-dashboard
type: Opaque

---

apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-csrf
  namespace: kubernetes-dashboard
type: Opaque
data:
  csrf: ""

---

apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-key-holder
  namespace: kubernetes-dashboard
type: Opaque

---

kind: ConfigMap
apiVersion: v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-settings
  namespace: kubernetes-dashboard

---

kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kubernetes-dashboard
rules:
  # Allow Dashboard to get, update and delete Dashboard exclusive secrets.
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["kubernetes-dashboard-key-holder", "kubernetes-dashboard-certs", "kubernetes-dashboard-csrf"]
    verbs: ["get", "update", "delete"]
    # Allow Dashboard to get and update 'kubernetes-dashboard-settings' config map.
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["kubernetes-dashboard-settings"]
    verbs: ["get", "update"]
    # Allow Dashboard to get metrics.
  - apiGroups: [""]
    resources: ["services"]
    resourceNames: ["heapster", "dashboard-metrics-scraper"]
    verbs: ["proxy"]
  - apiGroups: [""]
    resources: ["services/proxy"]
    resourceNames: ["heapster", "http:heapster:", "https:heapster:", "dashboard-metrics-scraper", "http:dashboard-metrics-scraper"]
    verbs: ["get"]

---

kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
rules:
  # Allow Metrics Scraper to get metrics from the Metrics server
  - apiGroups: ["metrics.k8s.io"]
    resources: ["pods", "nodes"]
    verbs: ["get", "list", "watch"]

---

apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kubernetes-dashboard
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kubernetes-dashboard
subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard
    namespace: kubernetes-dashboard

---

apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubernetes-dashboard
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubernetes-dashboard
subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard
    namespace: kubernetes-dashboard

---

kind: Deployment
apiVersion: apps/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kubernetes-dashboard
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      k8s-app: kubernetes-dashboard
  template:
    metadata:
      labels:
        k8s-app: kubernetes-dashboard
    spec:
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: kubernetes-dashboard
          image: kubernetesui/dashboard:v2.5.1
          imagePullPolicy: Always
          ports:
            - containerPort: 8443
              protocol: TCP
          args:
            - --auto-generate-certificates
            - --namespace=kubernetes-dashboard
            # Uncomment the following line to manually specify Kubernetes API server Host
            # If not specified, Dashboard will attempt to auto discover the API server and connect
            # to it. Uncomment only if the default does not work.
            # - --apiserver-host=http://my-address:port
          volumeMounts:
            - name: kubernetes-dashboard-certs
              mountPath: /certs
              # Create on-disk volume to store exec logs
            - mountPath: /tmp
              name: tmp-volume
          livenessProbe:
            httpGet:
              scheme: HTTPS
              path: /
              port: 8443
            initialDelaySeconds: 30
            timeoutSeconds: 30
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsUser: 1001
            runAsGroup: 2001
      volumes:
        - name: kubernetes-dashboard-certs
          secret:
            secretName: kubernetes-dashboard-certs
        - name: tmp-volume
          emptyDir: {}
      serviceAccountName: kubernetes-dashboard
      nodeSelector:
        "kubernetes.io/os": linux
      # Comment the following tolerations if Dashboard must not be deployed on master
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule

---

kind: Service
apiVersion: v1
metadata:
  labels:
    k8s-app: dashboard-metrics-scraper
  name: dashboard-metrics-scraper
  namespace: kubernetes-dashboard
spec:
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    k8s-app: dashboard-metrics-scraper

---

kind: Deployment
apiVersion: apps/v1
metadata:
  labels:
    k8s-app: dashboard-metrics-scraper
  name: dashboard-metrics-scraper
  namespace: kubernetes-dashboard
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      k8s-app: dashboard-metrics-scraper
  template:
    metadata:
      labels:
        k8s-app: dashboard-metrics-scraper
    spec:
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: dashboard-metrics-scraper
          image: kubernetesui/metrics-scraper:v1.0.7
          ports:
            - containerPort: 8000
              protocol: TCP
          livenessProbe:
            httpGet:
              scheme: HTTP
              path: /
              port: 8000
            initialDelaySeconds: 30
            timeoutSeconds: 30
          volumeMounts:
          - mountPath: /tmp
            name: tmp-volume
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsUser: 1001
            runAsGroup: 2001
      serviceAccountName: kubernetes-dashboard
      nodeSelector:
        "kubernetes.io/os": linux
      # Comment the following tolerations if Dashboard must not be deployed on master
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
      volumes:
        - name: tmp-volume
          emptyDir: {} |
| --- |

把以上内容复制在电脑上新建recommended.yaml文件，然后复制进虚拟机（虚拟机内新建文件复制内容格式有几率会产生问题，报错Error: no objects passed to apply）

| sudo vim recommended.yaml
kubectl apply -f recommended.yaml |
| --- |

**1.3 安装完成后的检查**

这个时候pod状态可能会出现问题，不要慌，重启一下k8s服务或者重启一下网络或者重启一下虚拟机，如果以上步骤都不行可以查看日志去解决（亲测两次重启有效）

#### 2. dashboard端口设置

默认Dashboard只能集群内部访问，修改Service为NodePort类型，暴露到外部

| kubectl -n kubernetes-dashboard edit service kubernetes-dashboard 
或
kubectl edit svc kubernetes-dashboard -n kubernetes-dashboard |
| --- |

将type对应的参数修改为NodePort

#### 3. 创建dashboard访问账号

创建dash.yaml文件

| sudo vim dash.yaml |
| --- |

将以下内容复制

| apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kubernetes-dashboard |
| --- |

应用dash.yaml文件

| kubectl apply -f dash.yaml |
| --- |

应用成功后输出如下

如出现报错如下：Unable to connect to the server: net/http: request canceled (Client.Timeout exceeded while awaiting headers)，可能是网络问题检查网络，重启网络

#### 4. 获取dashboard的访问token

| kubectl -n kubernetes-dashboard get secret $(kubectl -n kubernetes-dashboard get sa/admin-user -o jsonpath="{.secrets[0].name}") -o go-template="{{.data.token | base64decode}}" |
| --- |

上面的token需复制下来，后面登录面板要用

也可通过命令查看证书token

| kubectl describe secret -n kubernetes-dashboard |
| --- |

#### 5. 访问dashboard

**5.1 获取端口号**

获取访问端口（后续用于访问dashboard的端口号）

| kubectl get svc -A |grep kubernetes-dashboard |
| --- |

#### 5.2 ip查看

查看dashboard服务运行在哪个节点上

| kubectl get pods -n kubernetes-dashboard -o wide |
| --- |

可以看到kubernetes-dashboard服务在k8s-worker2节点中

#### 5.3 访问地址

访问k8s-worker2节点的31644端口

谷歌浏览器无法访问，解决方法：鼠标点一下页面，直接键盘输入thisisunsafe，然后回车就直接进去了

将之前复制的token粘贴进去，成功登录。可以在面板点击集群，查看所有pod信息

也可以查看所有节点的状态

可以看到目前三个解决，都准备就绪，且可以看到每个节点的CPU、内存等情况

# 环境搭建
# 内网搭建
# k8s
# 场景搭建
# Kubernetes集群
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
一、基本概念
二、组件介绍
- 主要组件
- 其他组件

三、前期准备
- 1、安装 Docker
- 2、关闭防火墙
- 3、关闭交换内存
- 4、禁用SELinux
- 5、修改cgroups
- 6. 组件安装（kubelet、kubectl、kubeadm）
- 7. 克隆出worker机器

四、创建集群
- 1. 初始化（master）
- 2.配置.kube
- 3.配置.bash_profile
- 4. 配置网络

五、节点加入集群（k8s-worker1、k8s-worker2）
- 1. 加入集群命令获取（主节点）
- 2. 加入集群（子节点）
- 3. 查看集群节点（主节点）
- 4、子节点中使用kubectl命令

六、Kubernetes安装面板
- 1 安装 dashboard
- 2. dashboard端口设置
- 3. 创建dashboard访问账号
- 4. 获取dashboard的访问token
- 5. 访问dashboard
- 5.2 ip查看
- 5.3 访问地址

