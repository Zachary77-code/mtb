# MTB Chair Final Synthesis Report

## Analysis Output

这里是基于您提供的专家报告汇总生成的最终 MTB 报告。

---

# 分子肿瘤专家委员会 (MTB) 综合报告

## 1. 执行摘要 (Executive Summary)

:::exec-summary
患者: 70岁男性，乙状结肠中分化腺癌 IV期 (ypT4aN2aM1)
关键分子特征: KRAS G12C (11.5%), ATM (胚系), TMB-High (79 mut/MB), MSS
当前治疗: 氟泽雷赛 + 西妥昔单抗 (2025.10起，五线治疗)
核心建议: 继续当前方案，需密切监测肾功能及药物相互作用；后线首选减量TAS-102联合方案。
紧急程度: 常规 (但在肾功能监测上需紧急关注)
:::

**摘要**:
患者为70岁男性，IV期乙状结肠癌，携带罕见的 **KRAS G12C** 突变及 **ATM 胚系突变**。尽管为 MSS 型，但 TMB 极高 (79 mut/MB)。既往经历了四线治疗（含化疗、贝伐珠单抗、免疫、mRNA疫苗），且对呋喹替尼有严重肾毒性反应（肌酐 146 μmol/L，eGFR ~40 mL/min）。目前正在接受五线 **氟泽雷赛+西妥昔单抗** 治疗。MTB 建议继续当前方案，这是目前证据等级最高的选择 [[ref:T1|CodeBreaK 300|https://pubmed.ncbi.nlm.nih.gov/37870968/|PFS获益显著]] [Evidence A]。鉴于肾功能受损，后续治疗需严格避免肾毒性药物，优先考虑减量的 TAS-102 联合方案或针对 ATM 的 PARP 抑制剂试验。

---

## 2. 患者概况 (Patient Profile)

### Demographics
- **Age**: 70 years
- **Sex**: Male
- **ECOG PS**: 1
- **Height/Weight**: 165cm / 66kg

### Cancer Diagnosis
- **Primary Cancer**: 乙状结肠恶性肿瘤
- **Histology**: 中分化腺癌 (Moderately differentiated Adenocarcinoma)
- **Stage**: IV期 (ypT4aN2aM1)
- **Metastatic Sites**: 双肺多发转移 (最大 2.1×1.5cm)，肝脏 (既往已切除)
- **Current Status**: 五线治疗中，疗效待评估

### Comorbidities & Organ Function
- **Renal**: **慢性肾功能不全** (Cr 146 μmol/L, eGFR ~40 mL/min)，既往 TKI 相关急性肾损伤。
- **Cardiac**: 心脏支架植入史，高血压。
- **Metabolic**: 糖尿病。

---

## 3. 分子特征 (Molecular Profile)

### 3.1 主要驱动突变

| Gene | Variant | Type | VAF | Frequency (cBioPortal) | CIViC Level | Evidence |
|------|---------|------|-----|------------------------|-------------|----------|
| **KRAS** | **G12C** | Missense | 11.5% | 3-4% in CRC [[ref:C1|cBioPortal|https://www.cbioportal.org|Rare in CRC]] | Level A | [Evidence A] |
| **ATM** | **Germline** | Truncating | - | 5-7% in CRC | Level C | [Evidence C] |

**临床意义解读**:
- **KRAS G12C**: 核心治疗靶点。在 CRC 中，G12C 抑制剂单药会导致 EGFR 反馈性激活，必须联合抗 EGFR 抗体（如西妥昔单抗）使用 [[ref:P1|Nature Medicine|https://pubmed.ncbi.nlm.nih.gov/38052910|Divarasib+Cetuximab]]。
- **ATM (胚系)**: 提示同源重组修复缺陷 (HRD) 潜力，可能对 PARP 抑制剂或铂类敏感。

### 3.2 免疫治疗标志物
- **MSI/MMR 状态**: **MSS / pMMR** (微卫星稳定)
- **TMB**: **79 mut/Mb (High)**
    - *注*: MSS 型结直肠癌出现如此高的 TMB 极罕见，可能与 POLE/POLD1 突变或既往化疗诱导有关。解释了患者既往对免疫联合治疗曾有短暂获益 (SD)。
- **PD-L1**: CPS = 3 (22C3)
- **HER2**: 0 (阴性)

### 3.3 Co-Alterations
- **EGFR**: IHC 2+ (过表达，非扩增，提示抗 EGFR 抗体结合位点存在)
- **Ki-67**: +5% (注：此为术后残留病灶数据，不代表当前高负荷转移灶的增殖活性)

---

## 4. 治疗史回顾 (Treatment History)

:::timeline
- line: 1线
  date: 2022.08-2022.12
  regimen: 奥沙利铂+卡培他滨+贝伐珠单抗
  response: PR
  type: neoadjuvant
  note: 新辅助化疗，共5程

- line: 1线
  date: 2023.01
  regimen: 根治性手术
  response: TRG2
  type: surgery
  note: 切除原发灶+肝转移+淋巴结清扫 (5/19 阳性)

- line: 1线
  date: 2023.03-2023.05
  regimen: 奥沙利铂+卡培他滨
  response: -
  type: adjuvant
  note: 术后辅助化疗，3程

- line: 1线
  date: 2023.05-2023.08
  regimen: 卡培他滨单药
  response: -
  type: maint
  note: 维持治疗

- line: 2线
  date: 2023.08-2024.01
  regimen: 伊立替康+亚叶酸钙+5-FU+贝伐珠单抗
  response: SD
  type: pd
  note: 因CEA升高、肺结节增大换方案

- line: 2线
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
  note: 严重不良反应：急性肾损伤+肢体水肿

- line: 3线
  date: 2024.09
  regimen: 雷替曲塞+信迪利单抗
  response: -
  type: event
  note: 出现发热（疑似感染）

- line: 3线
  date: 2024.10-2025.02
  regimen: 雷替曲塞+信迪利单抗
  response: SD
  type: pd
  note: 病情暂时控制，CEA降低至17.2

- line: 4线
  date: 2025.02-2025.10
  regimen: 信迪利单抗+抗肿瘤新抗原mRNA疫苗
  response: PD
  type: pd
  note: 含KRAS G12C新抗原；副作用发热、II度血小板减少；肺转移增大

- line: 5线
  date: 2025.10-今
  regimen: 氟泽雷赛+西妥昔单抗
  response: 待评估
  type: current
  note: 当前治疗
:::

**Key Observations**:
- **铂类敏感**: 一线治疗获 PR，可能与 ATM 突变有关。
- **肾毒性高危**: 呋喹替尼导致严重肾损伤，限制了后续 TKI 的使用。
- **免疫获益有限**: 多次免疫联合治疗最佳疗效为 SD，符合 MSS/TMB-H 特征。

---

## 5. 药物/方案对比 (Regimen Comparison)

### 5.1 方案对比表

| Regimen | Evidence Level | 具体给药剂量 | 肾功能调整 (eGFR ~40) | ORR | mPFS | Key Toxicities | Access |
|---------|----------------|--------------|------------|-----|------|----------------|--------|
| **氟泽雷赛+西妥昔单抗** | **[A]** | 氟泽雷赛 600mg BID<br>西妥昔 500mg/m² Q2W | 无需调整<br>(需防脱水) | ~26% | 5.6m | 皮疹, 低镁血症 | 赠药/自费 |
| **TAS-102+贝伐珠单抗** | **[A]** | TAS-102 **20mg/m²** BID<br>贝伐 5mg/kg Q2W | **减量至20mg/m²**<br>(标准35mg/m²) | ~6-10% | 5-6m | 骨髓抑制, 乏力 | 医保 |
| **奥拉帕利 (PARP)** | **[C]** | 200mg BID | **减量至200mg**<br>(标准300mg) | ~10-20% | N/A | 贫血, 恶心 | 自费/超适应症 |

### 5.2 各方案详细说明

#### 方案 1: 氟泽雷赛 (Fulzerasib) + 西妥昔单抗 (Cetuximab)
**证据级别**: [Evidence A] (基于 CodeBreaK 300 研究 [[ref:T2|NCT04793958|https://clinicaltrials.gov/study/NCT04793958|Sotorasib+Panitumumab]])
**治疗定位**: 五线挽救治疗 (当前方案)

**给药方案**:
- **氟泽雷赛**: 600 mg 口服 BID，连续服用。
- **西妥昔单抗**: 500 mg/m² 静脉输注，每 2 周一次。

**器官功能调整**:
- **肾功能**: 该组合主要经肝代谢或蛋白水解，对 eGFR 40 mL/min 患者相对安全。无需调整起始剂量，但需严防腹泻导致的肾前性肾衰。

**科学依据**:
KRAS G12C 突变在 CRC 中会导致 EGFR 信号通路的反馈性激活。单独抑制 KRAS G12C 疗效有限（ORR <10%）。联合 EGFR 单抗可阻断反馈回路，显著提升疗效（ORR ~26-30%）。

#### 方案 2: TAS-102 + 贝伐珠单抗
**证据级别**: [Evidence A] (SUNLIGHT 研究 [[ref:P2|PMID: 37133585|https://pubmed.ncbi.nlm.nih.gov/37133585/|OS benefit]])
**治疗定位**: 后线标准治疗

**给药方案**:
- **TAS-102**: **20 mg/m²** 口服 BID，d1-5, d8-12，每 28 天一周期。
- **贝伐珠单抗**: 5 mg/kg 静脉输注，每 2 周一次。

**器官功能调整**:
- **CrCl 30-49 mL/min**: **必须减量**。标准剂量为 35 mg/m²，肾损患者推荐起始剂量 20 mg/m² [[ref:FDA|LONSURF Label|https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/207981s012lbl.pdf|Dose Adjustment]]。

### 5.3 禁用方案及原因
| 方案 | 禁用原因 | 证据来源 |
|------|----------|----------|
| **呋喹替尼 / 瑞戈非尼** | **严重肾毒性风险**。患者既往使用呋喹替尼发生 AKI，瑞戈非尼为同类药，交叉毒性风险极大。 | 病史记录 |
| **顺铂 / 高剂量甲氨蝶呤** | **绝对禁忌**。eGFR < 60 mL/min 禁用。 | FDA 说明书 |

---

## 6. 器官功能与剂量 (Organ Function & Dosing)

### 6.1 当前器官功能

| System | Parameter | Value | Normal Range | Status |
|--------|-----------|-------|--------------|--------|
| **Renal** | **Creatinine** | **146 μmol/L** | 57-97 | **⚠️ Impaired (G2)** |
| **Renal** | **eGFR** | **~40 mL/min** | >90 | **⚠️ Moderate Decrease** |
| Hepatic | Liver Mets | Resected | - | ✓ Stable |
| Cardiac | History | Stents | - | ⚠️ Monitor LVEF |

### 6.2 剂量调整（各药物）

| 药物 | 标准剂量 | 当前患者推荐剂量 | 调整依据 |
|------|----------|--------------|----------|
| **TAS-102** | 35 mg/m² BID | **20 mg/m² BID** | FDA Label: CrCl 30-49 mL/min |
| **奥拉帕利** | 300 mg BID | **200 mg BID** | FDA Label: CrCl 31-50 mL/min |
| **氟泽雷赛** | 600 mg BID | 600 mg BID | 主要经肝代谢，无需调整 |

### 6.3 药物相互作用 (Drug-Drug Interactions)

| 当前用药 | 风险等级 | 相互作用机制 | 处理建议 |
|----------|----------|--------------|----------|
| **硝苯地平** | ⚠️ 高风险 | CYP3A4 诱导 (KRAS抑制剂) | 监测血压，可能需换用赖诺普利 |
| **阿托伐他汀** | ⚠️ 高风险 | CYP3A4 诱导 | 监测血脂，建议换用瑞舒伐他汀 |
| **PPI (抑酸药)** | ❌ 禁忌 | pH 依赖性吸收 | 避免使用，改用抗酸剂 (间隔4h) |

---

## 7. 治疗路线图 (Treatment Roadmap)

### 7.1 当前推荐方案（详细）

#### 方案名称: 氟泽雷赛 + 西妥昔单抗
**证据等级**: [Evidence A]
**治疗定位**: 五线治疗 (维持中)

**科学依据**:
针对 KRAS G12C 突变，联合抑制 KRAS 和 EGFR 可克服原发性耐药。CodeBreaK 300 研究显示，类似方案（Sotorasib+Panitumumab）相比标准治疗显著延长 PFS（5.6 vs 2.2 个月）。

**给药方案**:
- **氟泽雷赛**: 600 mg PO BID，持续给药。
- **西妥昔单抗**: 500 mg/m² IV Q2W。

**毒性管理**:
- **皮肤毒性**: 预防性使用米诺环素 100mg PO QD + 润肤霜。
- **低镁血症**: 每次输注前监测镁离子，必要时补镁。
- **肾功能**: 避免腹泻导致的脱水。若发生 ≥G2 腹泻，立即暂停并补液。

**预期疗效**:
- 预期 ORR: ~26%
- 预期 mPFS: ~5.6 个月

### 7.2 后线选择（详细排序）

| 优先级 | 方案 | 证据等级 | 适用条件 | 关键数据 |
|--------|------|----------|----------|----------|
| 1 | **TAS-102 + 贝伐珠单抗** | [A] | 肾功能允许 (减量) | mOS 10.8m |
| 2 | **PARP 抑制剂 (奥拉帕利)** | [C] | ATM 胚系突变 | 篮子试验获益 |
| 3 | **双免疫 (CTLA-4+PD-1)** | [B] | TMB-High 挽救 | 需临床试验 |

### 7.3 治疗决策流程图

:::roadmap
- title: 当前方案 (五线)
  status: current
  regimen: 氟泽雷赛 + 西妥昔单抗
  actions:
    - 监测肾功能 (eGFR)
    - 预防皮疹 (米诺环素)
    - 监测药物相互作用 (血压/血脂)

- title: 若有效 (PR/SD)
  status: success
  regimen: 维持治疗
  actions:
    - 每 6-8 周 CT 评估
    - 持续至进展或毒性不耐受

- title: 若进展 (PD)
  status: danger
  regimen: TAS-102 + 贝伐珠单抗
  actions:
    - **必须减量**: TAS-102 20mg/m²
    - 考虑临床试验 (PARP抑制剂)
    - 避免使用呋喹替尼/瑞戈非尼
:::

---

## 8. 分子复查建议 (Re-biopsy / Liquid Biopsy)

**Timing**: 疾病进展 (PD) 时。
**Method**: **液体活检 (ctDNA)**。
- 理由: 患者肺部多发转移，组织活检可能有风险；ctDNA 可全面反映异质性。
**Panel**: 广谱 NGS Panel (包含 KRAS, EGFR, MET, BRAF, PIK3CA)。
**Target**:
- **获得性耐药突变**: 如 KRAS Y96D/C, G12D/V (对 G12C 抑制剂耐药)。
- **旁路激活**: 如 MET 扩增 (可能需加用 MET 抑制剂)。

---

## 9. 临床试验推荐 (Clinical Trials)

**筛选原则**: 必须考虑 **eGFR ~40 mL/min** 的限制。排除含呋喹替尼的试验。

### 推荐试验列表

#### 试验 1: [NCT06293014] - TAS-102 + Bevacizumab in mCRC
- **NCT 编号**: [[1]](#ref-nct-nct06293014)
- **试验名称**: TAS-102 联合贝伐珠单抗治疗难治性结直肠癌
- **试验分期**: Phase II
- **研究药物**: **TAS-102 + Bevacizumab**
- **研究中心**: 郑州 (河南肿瘤医院) 等
- **匹配原因**: 患者未用过 TAS-102，且该药允许肾损患者减量入组（需确认具体入组阈值）。
- **入组关键条件**: 既往标准治疗失败；器官功能允许（通常 CrCl ≥ 30）。

#### 试验 2: [NCT06764680] - TAS-102 + Sintilimab
- **NCT 编号**: [[2]](#ref-nct-nct06764680)
- **试验名称**: 口服化疗联合免疫治疗晚期结直肠癌
- **试验分期**: Phase II
- **研究药物**: **TAS-102 + 信迪利单抗**
- **研究中心**: 广州 (中山大学肿瘤防治中心)
- **匹配原因**: 结合了 TAS-102 的化疗作用和 TMB-High 的免疫潜在获益。
- **注意**: 需确认是否接受既往 PD-1 治疗过的患者。

#### 试验 3: [NCT05489211] - TROPION-PanTumor03
- **NCT 编号**: [[3]](#ref-nct-nct05489211)
- **试验名称**: Dato-DXd (Trop-2 ADC) 泛瘤种篮子试验
- **试验分期**: Phase II
- **研究药物**: **Datopotamab Deruxtecan (Dato-DXd)**
- **研究中心**: 广州、重庆、杭州
- **匹配原因**: ADC 药物在多线耐药 CRC 中显示潜力。
- **风险**: 需严格确认肾功能要求（通常要求 CrCl ≥ 30 或 60）。

#### 试验 4: [NCT05815290] - Cadonilimab in CRC
- **NCT 编号**: [[4]](#ref-nct-nct05815290)
- **试验名称**: 卡度尼利单抗 (PD-1/CTLA-4) 治疗晚期结直肠癌
- **试验分期**: Phase II
- **研究药物**: **Cadonilimab**
- **研究中心**: 北京 (医科院肿瘤医院)
- **匹配原因**: 双免疫治疗可能克服 MSS/TMB-High 患者对单药 PD-1 的耐药。卡度尼利单抗无明显肾毒性。

#### 试验 5: [NCT04793958] - CodeBreaK 300 (参考)
- **NCT 编号**: [[5]](#ref-nct-nct04793958)
- **试验名称**: Sotorasib + Panitumumab vs Standard of Care
- **状态**: Active (可能已停止招募，作为当前治疗的证据参考)
- **研究药物**: Sotorasib + Panitumumab

### 试验选择注意事项
- **排除条件**: 严禁参加含 **呋喹替尼 (Fruquintinib)** 的试验（如 NCT06168786），因既往严重肾毒性。
- **优先考虑**: 允许 CrCl 30-50 mL/min 的试验（通常为 TAS-102 相关或免疫类）。

---

## 10. 局部治疗建议 (Local Therapy)

**Indications**:
- 目前双肺多发转移，且处于进展期，暂不适合根治性局部治疗。
- **SBRT (立体定向放疗)**: 若当前靶向治疗有效，且后续出现 **寡进展 (Oligoprogression)**（如仅 1-2 个肺结节增大），可考虑 SBRT 控制耐药病灶，延长药物使用时间。

---

## 11. 核心建议汇总 (Core Recommendations)

### Recommended Treatment Plan
1.  **Immediate (Current)**: **氟泽雷赛 (600mg BID) + 西妥昔单抗 (500mg/m² Q2W)** - **[Evidence A]**
    -   **Rationale**: 针对 KRAS G12C 的最佳循证方案。
    -   **Safety**: 密切监测肾功能，预防皮疹，监测镁离子。

2.  **Next Line (Upon Progression)**: **TAS-102 (20mg/m² BID) + 贝伐珠单抗** - **[Evidence A]**
    -   **Critical**: 必须按肾功能减量（标准剂量的 60%）。

3.  **Alternative**: **PARP 抑制剂 (奥拉帕利)** - **[Evidence C]**
    -   基于 ATM 胚系突变，可尝试超适应症使用或入组篮子试验。

### Not Recommended (Critical!)
**DO NOT USE**:
1.  **呋喹替尼 / 瑞戈非尼**: **[Evidence: Patient History]** - 既往导致严重急性肾损伤 (AKI)，再次使用风险极高。
2.  **西妥昔单抗单药**: **[Evidence A]** - KRAS G12C 突变原发耐药，无效。
3.  **顺铂**: **[Evidence: FDA Label]** - 肾功能不全禁忌。

---

## 12. 参考文献 (References)

1.  [PMID: 37870968 - CodeBreaK 300 Trial](https://pubmed.ncbi.nlm.nih.gov/37870968/)
2.  [PMID: 37133585 - SUNLIGHT Trial (TAS-102+Bev)](https://pubmed.ncbi.nlm.nih.gov/37133585/)
3.  [PMID: 38052910 - Divarasib + Cetuximab](https://pubmed.ncbi.nlm.nih.gov/38052910/)
4.  [PMID: 37852034 - PARP Inhibitors in ATM mutated cancer](https://pubmed.ncbi.nlm.nih.gov/37852034/)
5.  [PMID: 37318031 - TMB in MSS CRC](https://pubmed.ncbi.nlm.nih.gov/37318031/)
6.  [[8]](#ref-fda-label - lonsurf (tas-102))
7.  [NCT06293014 - TAS-102 Trial](https://clinicaltrials.gov/study/NCT06293014)
8.  [[6]](#ref-cbioportal-- colorectal cancer data)
9.  [[7]](#ref-nccn-guidelines for colon cancer v1.2025)

---

## References

<a id="ref-nct-nct06293014"></a>**[1]** [NCT: NCT06293014](https://clinicaltrials.gov/study/NCT06293014)

<a id="ref-nct-nct06764680"></a>**[2]** [NCT: NCT06764680](https://clinicaltrials.gov/study/NCT06764680)

<a id="ref-nct-nct05489211"></a>**[3]** [NCT: NCT05489211](https://clinicaltrials.gov/study/NCT05489211)

<a id="ref-nct-nct05815290"></a>**[4]** [NCT: NCT05815290](https://clinicaltrials.gov/study/NCT05815290)

<a id="ref-nct-nct04793958"></a>**[5]** [NCT: NCT04793958](https://clinicaltrials.gov/study/NCT04793958)

<a id="ref-cbioportal-- colorectal cancer data"></a>**[6]** [cBioPortal: - Colorectal Cancer Data](https://www.cbioportal.org/study/summary?id=coadread_tcga)

<a id="ref-nccn-guidelines for colon cancer v1.2025"></a>**[7]** [NCCN: Guidelines for Colon Cancer v1.2025](https://www.nccn.org/guidelines)

<a id="ref-fda-label - lonsurf (tas-102)"></a>**[8]** [FDA: Label - LONSURF (TAS-102)](https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/207981s012lbl.pdf)
