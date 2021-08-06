##### 一、使用源文件运行

1. 先安装PyQt5，graphviz 这两个库以及从<https://graphviz.gitlab.io/download/>安装dot
2. 再打开该目录下的命令行，输入命令：`python 哈夫曼编译码器.py`

##### 二、使用打包好的exe文件

1. 打包文件，并将ui文件放入与exe同级

   例：

   ①用  Visual Studio Code  的终端中对  Huffman_decoding_device.py  文件进行打包，输入命令: `cxfreeze . \Huffman_decoding_device.py --base-name=win32gui --icon='ui/mainicon.ico'`。

   ②然后在py文件的同一级就会生成一个build文件夹，将其打开之后是exe.win-amd64-3.9文件夹，再双击打开，此时就可发现一个Huffman_decoding_device.exe文件

   ③再将与py文件同一级的ui文件拉入与Huffman_decoding_device.exe同一级。

   (个人尝试了pyinstaller，可打包之后的exe或多或少都会有点问题)

   有关Python打包exe文件的方法的博客: <https://zhuanlan.zhihu.com/p/355304094>

2. 双击哈夫曼编译码器.exe即可

**注:但这两种方式中，都须将对应文件与ui文件夹置于同一目录下**