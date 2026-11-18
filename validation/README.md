# 本地迁移验证

本记录验证软件能否脱离原研究目录运行，以及提取后的传统数值算法是否保持原行为。它不检验模型在不同恒星或区域的普适标定。科学输入和后验保存在忽略目录 `.local/`，不随 Git 分发。

在 Windows x64、Python 3.12.14 下，新建不继承系统 site-packages 的虚拟环境，从实际构建的 wheel 普通安装。`pip check` 通过，9 项测试覆盖精确源编号、相关误差、输入缺项、方法适用范围和资产篡改。记录的全部运行依赖见 [environment.json](environment.json) 和仓库根目录 `requirements-windows-py312.txt`；这份依赖锁定仅在 Windows 验证。

源 `6719035052475592576` 使用既有 DR3 平均 XP、原先验和种子 20853506，约 54 秒完成一次新拟合；20 个后验数组与历史结果逐元素一致。记录见 [single_source.json](single_source.json)。输入去除了组内恒星参数，因此本次不输出 Lacc/Mdot；Teff=4300 K 只保留为历史回归条件，不冒称新的公开校准值。34 个关键函数/类的 AST 与原实现一致，见 [core_extraction.json](core_extraction.json)。

单源运行通过 `python -I` 启动，安装模块实际来自新环境的 `site-packages`。文件审计钩子禁止读取新仓库之外的原研究项目，运行期间没有越界访问。另一次独立只读验收在非仓库工作目录调用 CLI，帮助和样例检查均退出 0；skill 的参考说明可独立读取。已检查生成的谱图和 corner 图；`review` 校验通过，重复汇总同一运行得到 2 条结果、1 颗独立恒星。

资产清单的 1,623 个文件均通过大小与 SHA256 校验；新缓存只从已存资料复制。本轮没有下载新的天文样本、训练模型或执行批量拟合。原项目的逐文件保留检查见 [original_preservation.json](original_preservation.json)。仓库不设 GitHub remote，尚未公开；Fang 模板许可缺口仍须在公开前解决。
