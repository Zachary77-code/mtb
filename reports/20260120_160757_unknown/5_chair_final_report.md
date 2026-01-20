# MTB Chair Final Synthesis Report

## Analysis Output

这里是基于您提供的专家报告汇总生成的最终 MTB 报告。

---

# 分子肿瘤委员会 (MTB) 综合报告

## 1. 执行摘要 (Executive Summary)

:::exec-summary
患者: 70岁男性，乙状结肠中分化腺癌，IV期 (ypT4aN2aM1)
关键分子特征: KRAS G12C (11.5%), ATM 胚系突变, TMB-H (79 mut/Mb), MSS
当前治疗: 氟泽雷赛 + 西妥昔单抗 (2025.10起，五线治疗)
核心建议: 维持当前双靶方案，严密监测肾功能；后线优先考虑 Pan-KRAS 临床试验或 TAS-102
紧急程度: 常规 (目前待评估，需关注肾毒性)
:::

**综合意见**:
患者为晚期结直肠癌，携带罕见的 **KRAS G12C** 突变及 **ATM 胚系突变**。尽管 TMB 极高 (79 mut/Mb)，但为 MSS 表型且既往免疫治疗获益有限，提示非典型免疫获益人群。目前正接受五线 **氟泽雷赛 (KRAS G12C 抑制剂) 联合西妥昔单抗** 治疗，这是基于机制最合理的方案 [[ref:R1|CodeBreaK 300|https://pubmed.ncbi.nlm.nih.gov/37870968|ORR 30%]] [Evidence B]。

**主要风险**: 患者存在 **CKD 3b期肾功能不全 (eGFR ~40 mL/min)** 及既往 TKI 相关急性肾损伤史。**绝对禁忌**再次使用呋喹替尼或瑞戈非尼。后续治疗需严格根据肾功能调整剂量。

---

## 2. 患者概况 (Patient Profile)

### Demographics
- **Age**: 70 years
- **Sex**: Male
- **ECOG PS**: 1
- **Height/Weight**: 165cm / 66kg

### Cancer Diagnosis
- **Primary Cancer**: 乙状结肠中分化腺癌
- **Histology**: 腺癌 (Adenocarcinoma)
- **Stage**: IV期 (ypT4aN2aM1) - 术后病理分期
- **Metastatic Sites**: 双肺多发转移 (最大 2.1×1.5cm)
- **Tumor Markers**: CEA 112 ng/mL (升高), CA-199 145 U/mL

### Comorbidities
- **Renal Impairment**: 肌酐 146 μmol/L (eGFR ~39-44 mL/min)，既往 TKI 相关急性肾损伤
- **Cardiovascular**: 高血压 (硝苯地平)，心脏支架植入史 (阿托伐他汀)
- **Endocrine**: 糖尿病 (达格列净，阿卡波糖)

---

## 3. 分子特征 (Molecular Profile)

### 3.1 主要驱动突变

| Gene | Variant | Type | VAF | Frequency (cBioPortal) | CIViC Level | Evidence |
|------|---------|------|-----|------------------------|-------------|----------|
| **KRAS** | **G12C** | SNV | 11.5% | 3-4% in CRC | Level A (Combo) | [Evidence A/B] |
| **ATM** | **Germline** | Truncation | - | 5-7% | Level C | [Evidence C] |

**临床意义解读**:
1.  **KRAS G12C**: 核心治疗靶点。单药抑制会导致 EGFR 反馈性激活，必须联合抗 EGFR 单抗 (如西妥昔单抗) [[ref:R2|KRYSTAL-1|https://pubmed.ncbi.nlm.nih.gov/36546659|Combo ORR higher]]。
2.  **ATM (胚系)**: 提示同源重组修复缺陷 (HRD)。解释了患者一线对奥沙利铂 (DNA损伤剂) 的敏感性 (PR, TRG2)。提示 PARP 抑制剂可能有效 (合成致死机制)。

### 3.2 免疫治疗标志物
- **MSI/MMR 状态**: **MSS / pMMR** (微卫星稳定/错配修复完整)
- **TMB**: **79 mut/Mb (High)**
    - **病理分析**: MSS 背景下的超高 TMB 高度提示 **POLE/POLD1** 突变 (超突变表型)。
    - **临床矛盾**: 尽管 TMB 高，患者既往免疫联合治疗 (信迪利单抗) 仅获 SD 或 PD，未达深度缓解，提示可能存在免疫逃逸或假性高 TMB。
- **PD-L1**: CPS = 3 (低表达)

### 3.3 阴性重要发现
- **BRAF V600E**: Negative (排除 BRAF 抑制剂)
- **HER2**: IHC 0 (排除抗 HER2 治疗)
- **NRAS**: Negative

---

## 4. 治疗史回顾 (Treatment History)

:::timeline
- line: 1线
  date: 2022.08-2022.12
  regimen: 奥沙利铂+卡培他滨+贝伐珠单抗 (5程)
  response: PR
  type: neoadjuvant
  note: 新辅助化疗，疗效显著

- line: 手术
  date: 2023.01
  regimen: 根治性手术
  response: TRG2
  type: surgery
  note: 切除原发灶+肝转移+淋巴结清扫；病理显示淋巴结 5/19(+)

- line: 1线(辅助)
  date: 2023.03-2023.05
  regimen: 奥沙利铂+卡培他滨 (3程)
  response: -
  type: adjuvant
  note: 术后辅助化疗

- line: 1线(维持)
  date: 2023.05-2023.08
  regimen: 卡培他滨单药
  response: -
  type: maint
  note: 维持治疗，双肺出现小结节

- line: 2线
  date: 2023.08-2024.01
  regimen: 伊立替康+亚叶酸钙+5-FU+贝伐珠单抗
  response: SD
  type: pd
  note: 疾病稳定

- line: 2线(维持)
  date: 2024.02-2024.06
  regimen: 卡培他滨单药
  response: -
  type: maint
  note: 维持治疗

- line: 3线
  date: 2024.07
  regimen: 呋喹替尼+信迪利单抗
  response: -
  type: event
  note: 严重不良反应：急性肾损伤+肢体水肿 (肾穿刺证实TKI相关)

- line: 3线(Re-challenge)
  date: 2024.09
  regimen: 雷替曲塞+信迪利单抗
  response: -
  type: event
  note: 出现发热，疑似感染

- line: 3线(Re-challenge)
  date: 2024.10-2025.02
  regimen: 雷替曲塞+信迪利单抗
  response: SD(缩小)
  type: pd
  note: 病情暂时控制，CEA 降至 17.2

- line: 4线
  date: 2025.02-2025.10
  regimen: 信迪利单抗+抗肿瘤新抗原mRNA疫苗 (含KRAS G12C抗原)
  response: PD
  type: pd
  note: 肺转移增大，CEA 升至 112；副作用：发热，II度血小板减少

- line: 5线(当前)
  date: 2025.10-今
  regimen: 氟泽雷赛+西妥昔单抗
  response: 待评估
  type: current
  note: 首次针对 KRAS G12C 靶向治疗
:::

**Key Observations**:
1.  **Platinum Sensitivity**: 1L Oxaliplatin achieved PR/TRG2 (consistent with ATM mutation).
2.  **Renal Toxicity**: Severe AKI with Fruquintinib (3L).
3.  **IO Resistance**: Multiple IO lines (Sintilimab combos) failed to produce durable response despite high TMB.

---

## 5. 药物/方案对比 (Regimen Comparison)

### 5.1 方案对比表

| Regimen | Evidence Level | 具体给药剂量 | 肾功能调整 (eGFR ~40) | ORR | mPFS | Key Toxicities | Access |
|---------|----------------|--------------|-----------------------|-----|------|----------------|--------|
| **氟泽雷赛 + 西妥昔单抗** (Current) | **[B]** | 氟: 600mg BID<br>西: 500mg/m² q2w | 氟: 密切监测<br>西: 无需调整 | ~30% | ~5.6m | 腹泻, 皮疹, 低镁 | 中国上市/试验 |
| **TAS-102 + 贝伐珠单抗** (Next) | **[A]** | TAS: 35mg/m² BID d1-5,8-12<br>贝: 5mg/kg q2w | **TAS: 减量至 20mg/m²**<br>贝: 慎用 | 6.3% | 5.6m | 骨髓抑制, 恶心 | 医保 |
| **奥拉帕利** (Exploratory) | **[C]** | 300mg BID | **减量至 200mg BID** | N/A | N/A | 贫血, 疲劳 | 超适应症 |

### 5.2 各方案详细说明

#### 方案 1: 氟泽雷赛 (Fulzerasib) + 西妥昔单抗 (Cetuximab)
**证据级别**: [Evidence B] (基于同类药物及 IBI351 早期数据)
**治疗定位**: 五线挽救治疗 (当前方案)

**给药方案**:
- **氟泽雷赛**: 600mg PO BID (需依说明书确认)
- **西妥昔单抗**: 500 mg/m² IV Q2W

**器官功能调整**:
- **肾功能**: 氟泽雷赛尚无重度肾损数据。建议密切监测肌酐，若较基线升高 >25% 暂停。西妥昔单抗无需调整。
- **科学依据**: KRAS G12C 抑制剂单药有效率低，联合 EGFR 单抗可阻断反馈性通路激活 [[ref:R3|Nature Medicine 2024|https://pubmed.ncbi.nlm.nih.gov/38052910|Divarasib+Cetuximab]]。

#### 方案 2: TAS-102 (曲氟尿苷替匹嘧啶) ± 贝伐珠单抗
**证据级别**: [Evidence A] (SUNLIGHT 研究)
**治疗定位**: 后线标准治疗

**给药方案**:
- **TAS-102**: 标准剂量 35 mg/m² PO BID。
- **贝伐珠单抗**: 5 mg/kg IV Q2W。

**器官功能调整**:
- **CrCl 30-50 mL/min**: **必须减量**。推荐起始剂量 **20 mg/m² BID**。FDA 标签提示中度肾损患者暴露量增加，骨髓抑制风险显著升高。

### 5.3 禁用方案及原因
| 方案 | 禁用原因 | 证据来源 |
|------|----------|----------|
| **呋喹替尼 / 瑞戈非尼** | **既往严重肾毒性 (AKI)** | 既往病史 / 肾穿刺结果 |
| **顺铂 (Cisplatin)** | 肾功能不全 (eGFR < 60) | FDA 说明书 |

---

## 6. 器官功能与剂量 (Organ Function & Dosing)

### 6.1 当前器官功能
| System | Parameter | Value | Status |
|--------|-----------|-------|--------|
| **Renal** | **Creatinine** | **146 μmol/L** | ⚠️ **Impaired (CKD 3b)** |
| **Renal** | **eGFR** | **~39-44 mL/min** | ⚠️ **Critical Constraint** |
| Hepatic | ALT/AST | Normal | ✓ Normal |
| Cardiac | History | Stent | ✓ Stable (Monitor QTc) |

### 6.2 剂量调整 (关键药物)
| 药物 | 标准剂量 | 当前患者建议剂量 | 调整依据 |
|------|----------|------------------|----------|
| **TAS-102** | 35 mg/m² BID | **20 mg/m² BID** | CrCl 30-50 mL/min 需减量 |
| **奥拉帕利** | 300 mg BID | **200 mg BID** | CrCl 31-50 mL/min 需减量 |
| **西妥昔单抗** | 500 mg/m² | 标准剂量 | 大分子不经肾排泄 |

### 6.3 药物相互作用 (Oncologist Report)
| 当前用药 | 风险等级 | 相互作用机制 | 处理建议 |
|----------|----------|--------------|----------|
| **硝苯地平** | ⚡ 中风险 | CYP3A4 相互作用 | 监测血压 (KRASi 可能改变浓度) |
| **阿托伐他汀** | ⚡ 中风险 | CYP3A4 相互作用 | 监测肌痛 (横纹肌溶解风险) |
| **达格列净** | ⚠️ 高风险 | 血容量减少 | **若出现腹泻/呕吐，立即停用**以防 AKI |

---

## 7. 治疗路线图 (Treatment Roadmap)

### 7.1 当前推荐方案 (详细)

#### 方案名称: 氟泽雷赛 + 西妥昔单抗
**证据等级**: [Evidence B]
**治疗定位**: 针对 KRAS G12C 的精准治疗

**科学依据**:
患者携带 KRAS G12C 突变。单纯抑制 KRAS 会导致 EGFR 信号反馈性上调。联合西妥昔单抗可双重阻断 MAPK 通路，显著提高 ORR (从单药 <10% 提升至 ~30%)。

**毒性管理**:
1.  **皮肤毒性**: 预防性使用多西环素 100mg BID + 氢化可的松软膏。
2.  **腹泻**: 备好洛哌丁胺。若出现腹泻，**立即停用达格列净**以保护肾功能。
3.  **低镁血症**: 西妥昔单抗常见副作用，需每次输注前监测电解质。

**预期疗效**:
- 预期 ORR: ~30%
- 预期 mPFS: ~5.6 个月

### 7.2 后线选择 (详细排序)
| 优先级 | 方案 | 证据等级 | 适用条件 | 关键数据 |
|--------|------|----------|----------|----------|
| 1 | **Pan-KRAS 临床试验** | [Evidence C] | 肾功能允许入组 | 克服 G12C 耐药 |
| 2 | **TAS-102 ± 贝伐** | [Evidence A] | 需严格减量 | mPFS 5.6m (SUNLIGHT) |
| 3 | **奥拉帕利 (PARP)** | [Evidence C] | ATM 胚系突变 | 篮子试验数据支持 |

### 7.3 治疗决策流程图

:::roadmap
- title: 当前方案 (五线)
  status: current
  regimen: 氟泽雷赛 + 西妥昔单抗
  actions:
    - 每2周查肾功能/电解质
    - 预防皮疹
    - 停用达格列净(若腹泻)

- title: 若有效 (PR/SD)
  status: success
  regimen: 维持治疗
  actions:
    - 直至进展或毒性不耐受
    - 密切监测肌酐变化

- title: 若进展 (PD)
  status: danger
  regimen: 临床试验 / TAS-102
  actions:
    - 优先 Pan-KRAS 试验 (BGB-53038)
    - 备选 TAS-102 (减量)
    - 考虑奥拉帕利 (ATM靶向)
:::

---

## 8. 分子复查建议 (Re-biopsy)

**Timing**: 影像学确认进展 (PD) 时。
**Method**: 液体活检 (ctDNA) 优选（避免侵入性操作）。
**Panel**: 广谱 NGS Panel。
**检测目标**:
1.  **获得性 KRAS 突变**: 如 Y96D, G12D/V (提示对 G12C 抑制剂耐药)。
2.  **MET 扩增**: 常见的旁路耐药机制 (可联合 MET 抑制剂)。
3.  **MAPK 通路激活**: BRAF, MAP2K1 突变。

---

## 9. 临床试验推荐 (Clinical Trials)

**重要提示**: 患者 **eGFR ~40 mL/min** 是入组的最大障碍。需优先筛选允许轻中度肾损 (CrCl > 30-40) 的试验。

### 推荐试验列表 (完整保留 Recruiter 报告)

#### 试验 1 (最优先): [NCT06585488] - BGB-53038 (Pan-KRAS)
- **NCT 编号**: NCT06585488
- **试验名称**: BGB-53038 单药或联合治疗晚期实体瘤的 I 期研究
- **阶段**: Phase I
- **研究药物**: **BGB-53038 (Pan-KRAS 抑制剂)**
- **靶点**: KRAS 突变 (包括 G12C 耐药后)
- **招募状态**: Recruiting
- **研究中心**: 北京 (医科院肿瘤/北肿)、太原
- **匹配原因**: Pan-KRAS 抑制剂有望克服 G12C 抑制剂产生的耐药突变。
- **入组关键条件**: 需确认是否接受 eGFR ~40 的患者 (I期通常较严)。

#### 试验 2: [NCT06607185] - LY4066434 (Pan-KRAS)
- **NCT 编号**: NCT06607185
- **试验名称**: LY4066434 治疗 KRAS 突变实体瘤
- **阶段**: Phase I
- **研究药物**: **LY4066434**
- **靶点**: KRAS 突变
- **招募状态**: Recruiting
- **研究中心**: 北京、杭州、济南、上海、天津
- **匹配原因**: 另一款 Pan-KRAS 抑制剂，提供更多入组机会。

#### 试验 3: [NCT06825624] - HS-20093 (B7-H3 ADC)
- **NCT 编号**: NCT06825624
- **试验名称**: HS-20093 联合治疗晚期结直肠癌
- **阶段**: Phase I
- **研究药物**: **HS-20093 (B7-H3 ADC)**
- **靶点**: B7-H3 (CRC 通常高表达)
- **招募状态**: Recruiting
- **研究中心**: 杭州 (浙二)
- **匹配原因**: ADC 药物机制不同于 TKI，可能避开激酶耐药通路。

#### 试验 4: [NCT05489211] - Dato-DXd (TROP2 ADC)
- **NCT 编号**: NCT05489211
- **试验名称**: Dato-DXd 泛瘤种篮子试验
- **阶段**: Phase II
- **研究药物**: **Datopotamab Deruxtecan (TROP2 ADC)**
- **靶点**: TROP2
- **招募状态**: Recruiting
- **研究中心**: 广州、长沙、重庆、杭州
- **匹配原因**: TROP2 ADC 在肠癌中有一定数据。

#### 试验 5: [NCT05123482] - AZD8205 (PARP1 选择性抑制剂)
- **NCT 编号**: NCT05123482
- **试验名称**: AZD8205 治疗晚期实体瘤
- **阶段**: Phase I/II
- **研究药物**: **AZD8205**
- **靶点**: PARP1 / ATM 突变
- **招募状态**: Recruiting
- **研究中心**: 北京、长沙、重庆
- **匹配原因**: 针对患者的 **ATM 胚系突变** 进行合成致死治疗。

---

## 10. 局部治疗建议 (Local Therapy)

**Current Status**: 双肺多发转移，最大 2.1×1.5cm，处于进展期 (PD)。
**Recommendation**:
- 目前以全身系统治疗为主 (氟泽雷赛+西妥昔单抗)。
- **Oligoprogression (寡进展)**: 若全身大部分病灶控制良好，仅个别肺结节增大，可考虑 **SBRT (立体定向放疗)** 或 **射频消融 (RFA)**，以延长系统治疗时间。
- **Symptomatic**: 若出现气道压迫或咯血，考虑姑息性放疗。

---

## 11. 核心建议汇总 (Core Recommendations)

### Recommended Treatment Plan
1.  **Immediate (Current)**: **氟泽雷赛 (600mg BID) + 西妥昔单抗 (500mg/m² q2w)** - **[Evidence B]**
    - **Rationale**: 机制最匹配的靶向方案。
    - **Safety**: 密切监测肌酐 (每2周)。

2.  **Next Step (Upon Progression)**:
    - **Clinical Trial**: 优先 Pan-KRAS (BGB-53038) 或 PARP 抑制剂试验 - **[Evidence C]**
    - **Standard Care**: TAS-102 (需减量至 20mg/m² BID) ± 贝伐珠单抗 - **[Evidence A]**

3.  **Supportive Care**:
    - **Renal Protection**: 避免脱水，腹泻时停用达格列净。
    - **Skin Care**: 预防性使用多西环素。

### Not Recommended (Critical!)
**DO NOT USE**:
1.  ❌ **呋喹替尼 / 瑞戈非尼**: 既往发生严重 TKI 相关肾损伤，再挑战风险极高。
2.  ❌ **顺铂**: 绝对禁忌 (eGFR < 60)。
3.  ❌ **PD-1 单药**: MSS 且既往免疫治疗无效，单药无获益证据。

---

## 12. 参考文献 (References)

1.  [PMID: 37870968 - CodeBreaK 300 (Sotorasib + Panitumumab)](https://pubmed.ncbi.nlm.nih.gov/37870968/)
2.  [PMID: 36546659 - KRYSTAL-1 (Adagrasib + Cetuximab)](https://pubmed.ncbi.nlm.nih.gov/36546659/)
3.  [PMID: 38052910 - Divarasib plus cetuximab in KRAS G12C CRC](https://pubmed.ncbi.nlm.nih.gov/38052910/)
4.  [PMID: 37133585 - SUNLIGHT Trial (TAS-102 + Bevacizumab)](https://pubmed.ncbi.nlm.nih.gov/37133585/)
5.  [PMID: 40715048 - Fulzerasib (IBI351) Early Data](https://pubmed.ncbi.nlm.nih.gov/40715048/)
6.  [PMID: 41424250 - ATM mutation in CRC](https://pubmed.ncbi.nlm.nih.gov/41424250/)
7.  [NCCN Guidelines for Colon Cancer v1.2025](https://www.nccn.org/guidelines)
8.  [FDA Label - Lonsurf (TAS-102)](https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/207981s008lbl.pdf)