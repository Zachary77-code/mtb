# MTB Chair Final Synthesis Report

## Analysis Output

这里是基于您提供的专家报告汇总生成的最终 MTB 报告。

---

# 分子肿瘤专家委员会 (MTB) 综合报告

## 1. 执行摘要 (Executive Summary)

:::exec-summary
患者: 70岁男性，乙状结肠中分化腺癌，ypT4aN2aM1 (IV期)
关键分子特征: KRAS G12C (11.5%), ATM 胚系突变, MSS, TMB-H (79 mut/Mb)
当前治疗: 氟泽雷赛 + 西妥昔单抗 (2025.10起，五线治疗)
核心建议: 继续当前方案，每周监测肾功能；管理药物相互作用（停用阿托伐他汀）。
紧急程度: 常规 (密切监测安全性)
:::

**摘要**:
患者为70岁男性晚期结直肠癌患者，携带罕见的 **KRAS G12C** 突变及 **ATM 胚系突变**。尽管为 MSS 表型，但具有极高的 TMB (79 mut/Mb)，提示可能存在 POLE/POLD1 聚合酶校对缺陷。既往因使用呋喹替尼导致严重肾损伤 (Cr 146 μmol/L)，限制了后续治疗选择。目前接受氟泽雷赛联合西妥昔单抗治疗，这是基于循证医学的最佳选择 [[ref:P2|CodeBreaK 300|https://pubmed.ncbi.nlm.nih.gov/40215429|Evidence A]]。建议维持当前治疗，严密监测肾功能，后续若进展优先考虑针对 ATM 或 TMB-H 特征的临床试验。

---

## 2. 患者概况 (Patient Profile)

### Demographics
- **Age**: 70 years
- **Sex**: Male
- **ECOG PS**: 1
- **Height/Weight**: 165cm / 66kg

### Cancer Diagnosis
- **Primary Cancer**: 乙状结肠恶性肿瘤
- **Histology**: 中分化腺癌 (Moderately Differentiated Adenocarcinoma)
- **Stage**: ypT4aN2aM1 (IV期)
- **Metastatic Sites**: 双肺多发转移 (最大 2.1×1.5cm)；既往肝转移 (已切除)
- **Date of Diagnosis**: 2022.08 (初诊)

### Comorbidities
- **Renal**: **TKI相关肾损害** (既往肾穿刺证实)，慢性肾脏病 CKD 3b期 (Cr 146 μmol/L, eGFR ~39 mL/min)。
- **Cardiovascular**: 高血压，心脏支架术后。
- **Metabolic**: 糖尿病。

---

## 3. 分子特征 (Molecular Profile)

### 3.1 主要驱动突变

| Gene | Variant | Type | VAF | Frequency (CRC) | CIViC Level | Evidence |
|------|---------|------|-----|-----------------|-------------|----------|
| **KRAS** | **G12C** | Missense | 11.5% | 3-4% [[ref:P1|PMID:37432264|https://pubmed.ncbi.nlm.nih.gov/37432264/]] | Level A | [Evidence A] |
| **ATM** | **Germline** | Truncating | - | 5-10% | Level C | [Evidence C] |

**临床意义解读**:
- **KRAS G12C**: 结直肠癌中的罕见亚型。单药抑制剂因 EGFR 反馈性激活疗效有限，必须联合抗 EGFR 单抗（如西妥昔单抗）[[ref:P5|PMID:38052910|https://pubmed.ncbi.nlm.nih.gov/38052910/]]。
- **ATM 胚系突变**: 提示同源重组修复 (HRR) 缺陷，可能对 PARP 抑制剂或 ATR 抑制剂敏感 [[ref:P3|PMID:41424250|https://pubmed.ncbi.nlm.nih.gov/41424250/]]。建议进行家系遗传咨询。

### 3.2 免疫治疗标志物
- **MSI/MMR 状态**: **MSS / pMMR** (MLH1+, PMS2+, MSH2+, MSH6+)
- **TMB**: **79 mut/Mb (High)**。
  - *注*: MSS 肠癌通常 TMB <10。此患者 "MSS + Ultra-high TMB" 高度提示 **POLE/POLD1** 聚合酶校对结构域突变（超突变表型）。这解释了为何患者既往在三线免疫联合化疗中曾获益。
- **PD-L1**: CPS = 3 (22C3)。
- **Ki-67**: +5% (低增殖指数，反映既往治疗抑制效应)。

### 3.3 阴性发现
- **BRAF V600E**: Negative (排除 BRAF 抑制剂)。
- **HER2**: IHC 0 (排除抗 HER2 疗法)。

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
  note: 术后辅助化疗 (3程)

- line: 1线
  date: 2023.05-2023.08
  regimen: 卡培他滨单药
  response: -
  type: maint
  note: 维持治疗，发现双肺小结节

- line: 进展
  date: 2023.08
  regimen: 疾病进展
  response: PD
  type: pd
  note: CEA升高，双肺结节增大

- line: 2线
  date: 2023.08-2024.01
  regimen: 伊立替康+亚叶酸钙+5-FU+贝伐珠单抗
  response: SD
  type: current
  note: FOLFIRI+Bev

- line: 2线
  date: 2024.02-2024.06
  regimen: 卡培他滨单药
  response: -
  type: maint
  note: 维持治疗

- line: 3线
  date: 2024.07
  regimen: 呋喹替尼+信迪利单抗
  response: Toxicity
  type: event
  note: 严重不良反应：急性肾损伤+肢体水肿 (肾穿刺证实TKI相关)

- line: 3线
  date: 2024.09
  regimen: 雷替曲塞+信迪利单抗
  response: -
  type: event
  note: 出现发热

- line: 3线
  date: 2024.10-2025.02
  regimen: 雷替曲塞+信迪利单抗
  response: SD (缩小)
  type: current
  note: 病情暂时控制，CEA降低

- line: 4线
  date: 2025.02-2025.10
  regimen: 信迪利单抗+抗肿瘤新抗原mRNA疫苗
  response: PD
  type: current
  note: 含KRAS G12C新抗原；副作用：发热，II度血小板减少

- line: 5线 (当前)
  date: 2025.10-今
  regimen: 氟泽雷赛+西妥昔单抗
  response: 待评估
  type: current
  note: 针对KRAS G12C靶向治疗
:::

---

## 5. 药物/方案对比 (Regimen Comparison)

### 5.1 方案对比表

| Regimen | Evidence Level | 具体给药剂量 | 肾功能调整 (eGFR ~39) | ORR | mPFS | Key Toxicities | Status |
|---------|----------------|--------------|------------|-----|------|----------------|--------|
| **氟泽雷赛 + 西妥昔单抗** | **[Evidence B]** | 氟泽雷赛: 标准剂量 PO<br>西妥昔: 500mg/m² q2w | 密切监测，若Cr升高>25%需减量 | ~30-40% | ~6m | 腹泻、皮疹、潜在肾毒性 | **当前首选** |
| **TAS-102 + 贝伐珠单抗** | **[Evidence A]** | TAS-102: 35mg/m² bid d1-5,8-12<br>贝伐: 5mg/kg q2w | CrCl 30-89: 无需调整<br>CrCl <30: 减至20mg/m² | ~6-10% | 5.6m | 骨髓抑制 | **后线备选** |
| **ATR 抑制剂 (IMP9064)** | **[Evidence C]** | 临床试验剂量 | 需符合试验入组标准 (通常Cr≤1.5xULN) | N/A | N/A | 贫血、中性粒减少 | **试验推荐** |

### 5.2 各方案详细说明

#### 方案 1: 氟泽雷赛 (Fulzerasib) + 西妥昔单抗 (Cetuximab)
**证据级别**: [Evidence B] (基于 KRYSTAL-10, CodeBreaK 300 及 IBI351 数据)
**治疗定位**: 五线挽救治疗
**给药方案**:
- **氟泽雷赛**: [标准剂量] PO BID (具体参照说明书)
- **西妥昔单抗**: 500 mg/m² IV Q2W
**器官功能调整**:
- 尚无 eGFR <40 的明确剂量指南。建议标准剂量起始。
- **监测**: 若肌酐较基线升高 >25%，暂停并减量。
**科学依据**:
KRAS G12C 突变会导致 EGFR 通路反馈性激活。联合 EGFR 单抗可阻断此反馈环路。CodeBreaK 300 研究显示联合治疗组 PFS 显著优于标准治疗 [[ref:P2|PMID:40215429|https://pubmed.ncbi.nlm.nih.gov/40215429/]]。中国原研药氟泽雷赛显示出类似疗效 [[ref:P9|PMID:40715048|https://pubmed.ncbi.nlm.nih.gov/40715048/]]。

#### 方案 2: TAS-102 + 贝伐珠单抗
**证据级别**: [Evidence A] (SUNLIGHT Trial)
**治疗定位**: 六线标准治疗
**给药方案**:
- **TAS-102**: 35 mg/m² PO BID, d1-5, d8-12, q4w
- **贝伐珠单抗**: 5 mg/kg IV Q2W
**器官功能调整**:
- CrCl 30-89 mL/min: 无需调整 (患者符合)。
- CrCl <30 mL/min: 起始剂量减至 20 mg/m²。
**科学依据**:
SUNLIGHT 研究证实，TAS-102 联合贝伐珠单抗较单药显著延长 OS (10.8 vs 7.5 个月) [[ref:S1|PMID:37133585|https://pubmed.ncbi.nlm.nih.gov/37133585/]]。

### 5.3 禁用方案及原因
| 方案 | 禁用原因 | 证据来源 |
|------|----------|----------|
| **瑞戈非尼 / 呋喹替尼** | **绝对禁忌**：既往发生 TKI 相关严重肾损伤，再挑战极高风险导致透析。 | [Patient History] |
| **奥沙利铂再挑战** | 获益低，且有神经毒性风险。 | [NCCN Guidelines] |

---

## 6. 器官功能与剂量 (Organ Function & Dosing)

### 6.1 当前器官功能
| System | Parameter | Value | Status | Action |
|--------|-----------|-------|--------|--------|
| **Renal** | **Cr / eGFR** | **146 μmol/L / ~39 mL/min** | **⚠️ Impaired (CKD 3b)** | **主要限制因素** |
| Hepatic | ALT/AST | Normal | ✓ Normal | 常规监测 |
| Hematologic | PLT | 既往 II 度减少 | ⚠️ Watch | 需关注 |

### 6.2 剂量调整
- **氟泽雷赛**: 标准剂量起始。若出现 Grade ≥2 肾毒性或肌酐升高 >25%，暂停用药。
- **西妥昔单抗**: 无需根据肾功能调整，但需注意镁离子监测。

### 6.3 药物相互作用 (Critical DDIs)
**必须完整列出并处理**:

| 当前用药 | 风险等级 | 相互作用机制 | 处理建议 |
|----------|----------|--------------|----------|
| **阿托伐他汀** | ⚠️ 高风险 | KRAS G12C 抑制剂可能影响 CYP3A4，增加他汀血药浓度导致**横纹肌溶解**。 | **建议停用**，或换用瑞舒伐他汀 (低剂量)。 |
| **硝苯地平** | ⚡ 中风险 | CYP3A4 底物，可能导致血压波动。 | 每日监测血压。 |
| **达格列净** | ⚠️ 高风险 | SGLT2 抑制剂有利尿作用，加重腹泻引起的脱水，恶化肾功能。 | 若出现腹泻，**立即暂停**达格列净。 |

### 6.4 绝对禁忌药物
- **碘造影剂**: 禁止使用增强 CT (造影剂肾病风险)。**改用 MRI**。
- **肾毒性抗生素**: 避免使用氨基糖苷类。

---

## 7. 治疗路线图 (Treatment Roadmap)

### 7.1 当前推荐方案（详细）

#### 方案名称: 氟泽雷赛 + 西妥昔单抗
**证据等级**: [Evidence B]
**治疗定位**: 五线挽救治疗

**科学依据**:
针对 KRAS G12C 突变 (11.5%)。单药有效率低，联合抗 EGFR 可克服反馈性耐药 [[ref:P10|PMID:36546659|https://pubmed.ncbi.nlm.nih.gov/36546659/]]。

**毒性管理**:
| 毒性类型 | 预防措施 | 监测方案 | 处理原则 |
|----------|----------|----------|----------|
| **肾毒性** | 充分水化，避免脱水 | **每周查肾功能** | Cr >1.5x 基线暂停 |
| **皮肤毒性** | 多西环素 100mg bid | 每次访视 | 分级处理，外用激素 |
| **腹泻** | 易蒙停备用 | 每日排便次数 | 暂停达格列净，补液 |

**预期疗效**:
- 预期 ORR: ~30-40%
- 预期 mPFS: ~5-6 个月

### 7.2 后线选择（详细排序）

| 优先级 | 方案 | 证据等级 | 适用条件 | 关键数据 |
|--------|------|----------|----------|----------|
| 1 | **TAS-102 + 贝伐珠单抗** | [Evidence A] | 肾功能 eGFR >30 | OS 10.8m |
| 2 | **临床试验 (ATR抑制剂)** | [Evidence C] | ATM 突变，符合入组 Cr | 针对 DNA 修复缺陷 |
| 3 | **双免疫 (Nivo+Ipi)** | [Evidence C] | TMB-H, 体能允许 | 针对高 TMB |

### 7.3 治疗决策流程图

:::roadmap
- title: 当前方案 (五线)
  status: current
  regimen: 氟泽雷赛 + 西妥昔单抗
  actions:
    - 每周监测肾功能
    - 停用阿托伐他汀
    - 6-8周 MRI 评估

- title: 若有效 (PR/SD)
  status: success
  regimen: 维持治疗
  actions:
    - 继续直至进展
    - 严防腹泻脱水

- title: 若进展 (PD)
  status: danger
  regimen: TAS-102 + 贝伐 或 临床试验
  actions:
    - 优先评估 NCT05269316 (ATR)
    - 液体活检 (MET扩增?)
    - 启动 TAS-102 (注意剂量)
:::

---

## 8. 分子复查建议 (Re-biopsy / Liquid Biopsy)

**Timing**: 疾病进展 (PD) 时。
**Method**: 液体活检 (ctDNA)，因肺部病灶穿刺风险及肾功能限制。
**Panel**: 广谱 NGS Panel。
**Targets**:
- **KRAS 继发突变**: G12D, G12V, Y96D (影响后续 G12C 抑制剂选择)。
- **MET 扩增**: 潜在的耐药机制，可联合 MET 抑制剂。
- **EGFR 胞外域突变**: S492R 等 (提示西妥昔单抗耐药)。

---

## 9. 临床试验推荐 (Clinical Trials)

鉴于患者 **ATM 胚系突变** 和 **TMB-H (79)** 特征，推荐以下试验。**注意：肾功能 (Cr 146) 是主要入组障碍**。

### 推荐试验列表

#### 试验 1（最优先）: NCT05269316 - IMP9064 (ATR抑制剂)
- **NCT 编号**: [[1]](#ref-nct-nct05269316)
- **试验名称**: IMP9064单药或联合治疗晚期实体瘤
- **试验分期**: Phase I/II
- **研究药物**: **IMP9064 (ATR Inhibitor)**
- **靶点/适应症**: ATM 突变实体瘤
- **招募状态**: Recruiting
- **研究中心**: **北京肿瘤医院**
- **匹配原因**: 患者携带 ATM 胚系突变，ATR 抑制剂通过合成致死机制起效。
- **入组关键条件**: 晚期实体瘤；需确认 Cr 入组标准 (通常 ≤1.5xULN，患者处于临界值)。
- **早期数据**: ATR 抑制剂在 ATM 缺陷肿瘤中显示活性 [[ref:P3|PMID:41424250|https://pubmed.ncbi.nlm.nih.gov/41424250/]]。

#### 试验 2: NCT06139536 - 双免疫 (CTLA-4 + PD-1)
- **NCT 编号**: [[2]](#ref-nct-nct06139536)
- **试验名称**: BAT4706 (CTLA-4) + BAT1308 (PD-1) 治疗晚期实体瘤
- **试验分期**: Phase I
- **研究药物**: **BAT4706 + BAT1308**
- **靶点/适应症**: MSS CRC (Queue B) / 晚期实体瘤
- **招募状态**: Recruiting
- **研究中心**: **河南肿瘤医院**、临沂肿瘤医院
- **匹配原因**: 针对 MSS 但 TMB-H 的患者，双免疫可能克服单药耐药。
- **入组关键条件**: 既往标准治疗失败。

#### 试验 3: NCT05187338 - 三联免疫
- **NCT 编号**: [[3]](#ref-nct-nct05187338)
- **试验名称**: 三联免疫检查点抑制剂治疗晚期实体瘤
- **试验分期**: Phase I/II
- **研究药物**: **Ipilimumab + Pembrolizumab + Durvalumab**
- **靶点/适应症**: 晚期实体瘤
- **招募状态**: Recruiting
- **研究中心**: **广州医科大学附属第二医院**
- **匹配原因**: 强效免疫激活，针对高 TMB。
- **入组关键条件**: **Cr ≤ 145.5 μmol/L** (患者 146，极可能通过水化达标入组)。

### 试验选择注意事项
- **排除条件**: 排除 NCT05382559 (针对 KRAS G12D，患者为 G12C)。
- **肾功能障碍**: 建议优先联系 **广州 (NCT05187338)**，其公开的肌酐标准对本患者最友好。
- **地理位置**: 考虑患者居住地，北京、河南、广州均有中心。

---

## 10. 局部治疗建议 (Local Therapy)

**Current Status**: 双肺多发转移，无急症。
**Recommendation**:
- 目前**不建议**局部治疗 (No immediate indication)。
- **例外情况**: 若全身治疗有效，但出现个别病灶进展 (Oligoprogression)，可考虑 SBRT (立体定向放疗)。
- **骨转移**: 若出现骨痛，可考虑姑息放疗 (8 Gy x 1)。

---

## 11. 核心建议汇总 (Core Recommendations)

### Recommended Treatment Plan
1.  **Immediate (Current)**: **Fulzerasib + Cetuximab** - **[Evidence B]**
    - **Rationale**: KRAS G12C 靶向联合抗 EGFR，阻断耐药反馈环路。
    - **Safety**: 每周监测肾功能。若 Cr >1.5x 基线，暂停用药。

2.  **Supportive Care**:
    - **DDI Management**: 停用阿托伐他汀 (换用瑞舒伐他汀)；暂停达格列净若出现腹泻。
    - **Skin Care**: 预防性使用多西环素和保湿霜。

3.  **Next Line (If PD)**:
    - **Standard**: **TAS-102 + Bevacizumab** [Evidence A] (需根据肾功能调整剂量)。
    - **Trial**: **IMP9064 (ATR inhibitor)** [Evidence C] (针对 ATM 突变)。

### Not Recommended (Critical!)
**DO NOT USE**:
1.  **Regorafenib / Fruquintinib**: **[Contraindicated]** - 既往导致严重肾损伤，再挑战风险极高。
2.  **Iodine Contrast CT**: **[Contraindicated]** - 避免造影剂肾病，改用 MRI。
3.  **Single Agent IO**: **[Ineffective]** - 既往 PD-1 单药已耐药 (MSS)。

---

## 12. 参考文献 (References)

1.  [PMID: 37432264 - KRAS G12C Prevalence](https://pubmed.ncbi.nlm.nih.gov/37432264/)
2.  [PMID: 40215429 - CodeBreaK 300 Trial](https://pubmed.ncbi.nlm.nih.gov/40215429/)
3.  [PMID: 41424250 - ATM Mutation & PARP/ATR](https://pubmed.ncbi.nlm.nih.gov/41424250/)
4.  [PMID: 38052910 - Divarasib + Cetuximab](https://pubmed.ncbi.nlm.nih.gov/38052910/)
5.  [PMID: 40715048 - IBI351 (Fulzerasib) Data](https://pubmed.ncbi.nlm.nih.gov/40715048/)
6.  [PMID: 36546659 - KRYSTAL-1 Trial](https://pubmed.ncbi.nlm.nih.gov/36546659/)
7.  [PMID: 37133585 - SUNLIGHT Trial (TAS-102+Bev)](https://pubmed.ncbi.nlm.nih.gov/37133585/)
8.  [NCT05269316 - IMP9064 Trial](https://clinicaltrials.gov/study/NCT05269316)
9.  [NCT06139536 - Dual IO Trial](https://clinicaltrials.gov/study/NCT06139536)
10. [NCT05187338 - Triple IO Trial](https://clinicaltrials.gov/study/NCT05187338)
11. [[4]](#ref-nccn-guidelines for colon cancer v1.2025)

---

## References

<a id="ref-nct-nct05269316"></a>**[1]** [NCT: NCT05269316](https://clinicaltrials.gov/study/NCT05269316)

<a id="ref-nct-nct06139536"></a>**[2]** [NCT: NCT06139536](https://clinicaltrials.gov/study/NCT06139536)

<a id="ref-nct-nct05187338"></a>**[3]** [NCT: NCT05187338](https://clinicaltrials.gov/study/NCT05187338)

<a id="ref-nccn-guidelines for colon cancer v1.2025"></a>**[4]** [NCCN: Guidelines for Colon Cancer v1.2025](https://www.nccn.org/guidelines)
