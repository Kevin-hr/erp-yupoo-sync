## ERP 导入 Excel 标准（以 BAPE_0418.xlsx 为准）

### 权威模板
- 标准模板：templates/BAPE_0418.xlsx
- 输出模板：templates/商品导入模板 (修改版1.0).xlsx

### 行结构（多规格）
- 每个商品占 4 行：主行（Size:S）+ 3 行 SKU 子行（Size:M/L/XL）
- SKU 子行仅填写：AB（SKU值）、AD（售价）、AE（原价）、AF（库存）
- SKU 子行其他字段必须为空，否则可能导致“基础信息重复/覆盖”或导入失败

### 字段标准（关键列）
- B 商品标题*：必填；最多 255 字符；同一批次导入内必须唯一（重复会导致导入失败）
- D 商品描述：HTML 代码；推荐包含 Name: 字段（品牌链接 + 去品牌后的标题），并保持与 B 列一致
- E 商品首图*：单 URL；必须可访问；推荐使用 pic.yupoo.com 外链
- F 商品其他图片：多 URL；用换行分隔；单商品图片总数 ≤ 14（含首图）
- H 属性：多行，格式 `属性名|属性值`
- I 商品上架*：必须 N（下架）；禁止自动上架，需人工审核后再改 Y
- J 物流模板*：必须填写系统已配置模板；BAPE_0418 标准值为 Clothing
- K 类别名称：按品牌/类目配置；BAPE_0418 标准值为 BAPE
- L 标签：多个标签用英文逗号分隔；BAPE_0418 标准为 =B 列标题
- M 计量单位：按计量单位表；BAPE_0418 标准值为 件/个
- O 不记库存*：BAPE_0418 标准值为 Y
- P 商品重量*：kg；3 位小数；BAPE_0418 标准值为 0.3
- T SEO标题：动态生成；最多 5000 字符
- U SEO描述：动态生成；最多 5000 字符
- V SEO关键词：多个关键词用英文逗号分隔；BAPE_0418 标准为 =B 列标题
- W SEO URL Handle：允许英文/数字/短横线；BAPE_0418 标准示例为留空
- Y 规格2：固定值 `Size\nS\nM\nL\nXL`（多行换行格式）
- AB SKU值：主行 Size:S；SKU 子行 Size:M / Size:L / Size:XL
- AD 售价*：2 位小数
- AE 原价：2 位小数
- AF 库存：最多 9 位整数

### 标题去重规则（导入关键）
- 以主行（Size:S）的 B 列为商品唯一键
- 若出现重复标题：自动追加后缀 ` (2)`、` (3)`…，并保证总长度 ≤ 255
- 任何与标题绑定的字段（L/V/T/U/D(Name)）必须使用同一个“去重后标题”，避免不一致

### 参考实现（Gucci 转换器）
- 脚本：gucci_to_erp.py
- 输入：67款GucciT恤图片链接表_0419.xlsx
- 输出：GucciT恤_ERP导入模板_0419_BAPE标准对齐_标题去重.xlsx

### 可执行程序（Windows）
- 构建脚本：scripts/build_gucci_to_erp_exe.py
- 产物路径：dist/GucciToErp.exe
- 用法示例：
  - GucciToErp.exe --src 67款GucciT恤图片链接表_0419.xlsx --out 输出.xlsx
