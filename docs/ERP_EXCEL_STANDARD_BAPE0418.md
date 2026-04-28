# ERP 导入 Excel 标准

> **版本**: v2.0.0 (2026-04-27)
> **状态**: 🔒 **锁定 - 禁止修改**
> **验证来源**: `04-27_34款.xlsx` (2026-04-27 成功导入 34款商品)

---

## ⚠️ 红线规则

| 规则 | 说明 | 违规后果 |
|------|------|----------|
| **禁止修改此标准** | 本文档已锁定，任何修改需经审批 | 导入失败/数据不一致 |
| **I列必须 N** | 商品上架必须为 N（下架） | 违反业务合规性 |
| **SKU子行只填4列** | SKU子行仅填 AB/AD/AE/AF | 基础信息重复/覆盖 |
| **图片总数 ≤ 14** | 首图 + 其他图片 ≤ 14 | 导入失败 |
| **标题唯一** | B列标题必须唯一，重复需编号 | 导入失败 |

---

## 行结构（多规格）

- 每个商品占 **4 行**：主行（Size:S）+ 3 行 SKU 子行（Size:M/L/XL）
- SKU 子行仅填写：**AB（SKU值）、AD（售价）、AE（原价）、AF（库存）**
- SKU 子行其他字段必须为空

---

## 字段标准（33列）

### 必填字段

| 列 | 字段名 | 标准值 | 示例 |
|----|--------|--------|------|
| B | 商品标题* | 唯一标题，最多255字符 | `Louis Vuitton T-Shirt Print White` |
| E | 商品首图* | pic.yupoo.com URL | `http://pic.yupoo.com/lol2024/xxx.jpeg` |
| I | 商品上架* | **N**（下架） | N |
| J | 物流模板* | **Clothing** | Clothing |
| O | 不记库存* | **Y** | Y |
| P | 商品重量* | **0.3** | 0.3 |
| AD | 售价* | **59** | 59 |

### 固定值字段

| 列 | 字段名 | 标准值 | 说明 |
|----|--------|--------|------|
| H | 属性 | **材质\|棉质** | 固定值 |
| M | 计量单位 | **件/个** | 固定值 |
| Y | 规格2 | **Size\nS\nM\nL\nXL** | 换行分隔 |

### 动态生成字段

| 列 | 字段名 | 格式模板 |
|----|--------|----------|
| K | 类别名称 | 品牌名（从标题提取） |
| L | 标签 | = B列标题 |
| T | SEO标题 | `Stockx Replica Streetwear \| Top Quality 1:1 {标题} - stockxshoesvip.net` |
| U | SEO描述 | `Buy Best 1:1 Replica Clothing on Stockxshoesvip.net. Perfect {标题}. 100% safe shipping, free QC confirmation, and easy returns.` |
| V | SEO关键词 | = B列标题 |
| AB | SKU值 | 主行: `Size:S`，子行: `Size:M` / `Size:L` / `Size:XL` |
| AE | 原价 | **99** |
| AF | 库存 | **999** |

### 空白字段（不填写）

| 列 | 字段名 | 原因 |
|----|--------|------|
| A | 商品ID | 空=新增商品 |
| C | 副标题 | 不需要 |
| G | 关键信息 | 不需要 |
| N | 商品备注 | 不需要 |
| Q/R/S | 包装尺寸 | 不需要 |
| W | SEO URL Handle | 自动生成 |
| X | 规格1 | 不使用 |
| Z/AA | 规格3/4 | 不使用 |
| AC | SKU图片 | 不使用 |
| AG | SKU | 不使用 |

---

## D列 商品描述（HTML模板）

> **格式来源**: 2026-04-27 成功导入验证

### 结构

```
1. Name字段（品牌链接 + 去品牌后的标题）
2. Category字段（品牌Clothes链接）
3. More about段落（固定链接）
4. Our Core Guarantees
5. Shipping & Payment
6. About StockxShoesVIP
7. Contact Us
```

### 模板

```html
<p><span style="font-family: Tahoma;"><span>Name: <span style="font-family: verdana, geneva, sans-serif;"><a href="https://www.stockxshoesvip.net/{brand-slug}/" rel="noopener" target="_blank">{brand}</a> {name-without-brand}</span></span></span></p>
<p>Category: <span style="font-size: 14px;"><a href="https://www.stockxshoesvip.net/{brand-slug}-Clothes/" target="_self" class="third-link animation-underline">{brand}</a></span><a href="https://www.stockxshoesvip.net/{brand-slug}-Clothes/" target="_self"> Clothes</a></p>
<p><span style="font-weight: bold;">More about&nbsp;</span><span style="font-weight: bold;"></span></p>
<p><a href="https://www.stockxshoesvip.net/Fear-Of-God-Clothing/" rel="noopener" target="_blank">Fear Of God Clothing</a>&nbsp; <a href="https://www.stockxshoesvip.net/Pants/" rel="noopener" target="_blank">Pants</a>&nbsp; <a href="https://www.stockxshoesvip.net/Denim-Tears/" rel="noopener" target="_blank">Denim Tears</a></p>
<p><b>Our Core Guarantees</b></p>
<ul>
<li><b>Exclusive <a href="https://www.stockxshoesvip.net/Stockxshoes-QC-Pics/" rel="noopener" target="_blank">QC Service</a>:</b> We provide free Quality Control (QC) pictures before shipment. You approve the exact item you will receive&mdash;if not satisfied, we offer free exchanges or refunds.</li>
<li><b>Premium Packaging:</b> All apparel comes with full brand packaging and original tags.</li>
<li><b>Worry-Free Logistics:</b> We handle secure delivery and customs clearance to ensure your package arrives safely.</li>
<li><b>100% Safe Shopping:</b> 30-day money-back guarantee with damage protection.</li>
</ul>
<p><b>Shipping &amp; Payment</b></p>
<ul>
<li><b>Delivery Time:</b> 7-18 Days (Minor 1-3 day delays are normal). Tracking number provided.</li>
<li><b>Shipping Methods:</b> FedEx / USPS / DHL / UPS / EMS / Royal Mail.</li>
<li><b>Payment Methods:</b> Credit/Debit Card, PayPal, Bank Transfer, Cash App, Zelle.</li>
</ul>
<p><b>About StockxShoesVIP</b></p>
<p>With 10 years of offline retail and 5 years of online excellence, we are your trusted source for <b>premium replica sneakers and streetwear</b>.</p>
<p><i>(Note: We are an independent supplier and not affiliated with the StockX platform. Please bookmark our official site: stockxshoesvip.net)</i></p>
<p><b>Contact Us</b></p>
<ul>
<li><b>WhatsApp/WeChat:</b> +86 189 5920 5893</li>
<li><b>Instagram:</b> @stockxshoesvip_com</li>
</ul>
<p><i>Buy with confidence, wear with confidence.</i></p>
```

### 品牌URL映射

| 品牌 | URL Slug |
|------|----------|
| Louis Vuitton | Louis-Vuitton |
| Balenciaga | Balenciaga |
| CLOT | CLOT |
| Saint Laurent | Saint-Laurent |
| Celine | Celine |
| Prada | Prada |
| Fendi | Fendi |
| Dior | Dior |
| Loewe | Loewe |
| Dolce & Gabbana | Dolce-Gabbana |
| Givenchy | Givenchy |
| Burberry | Burberry |

---

## SKU 子行结构

| 行 | AB (SKU值) | AD (售价) | AE (原价) | AF (库存) |
|----|------------|-----------|-----------|-----------|
| 主行 | Size:S | 59 | 99 | 999 |
| 子行1 | Size:M | 59 | 99 | 999 |
| 子行2 | Size:L | 59 | 99 | 999 |
| 子行3 | Size:XL | 59 | 99 | 999 |

---

## 标题去重规则

- 以主行（Size:S）的 B 列为商品唯一键
- 若出现重复标题：自动追加后缀 ` (2)`、` (3)`…
- 保证总长度 ≤ 255
- 任何与标题绑定的字段（L/V/T/U/D(Name)）必须使用同一个"去重后标题"

---

## 参考实现

- 脚本：`scripts/csv_to_erp_excel.py`
- 输入：标准CSV（列：A序号, B标题, D首图, E其他图片）
- 输出：ERP导入Excel（33列，每商品4行）

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.0.0 | 2026-04-27 | 🔒 锁定版本；基于成功导入验证；完整字段标准 |
| v1.0.0 | 2026-04-18 | 初始版本（BAPE_0418.xlsx） |

---

> **最后更新**: 2026-04-27
> **验证文件**: `04-27_34款.xlsx` (34款商品成功导入)
