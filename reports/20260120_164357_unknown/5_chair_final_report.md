# MTB Chair Final Synthesis Report

## Analysis Output

这份 MTB 报告汇总了病理、分子遗传、临床试验及肿瘤内科专家的意见，针对患者复杂的分子特征（KRAS G12C, ATM, TMB-High）及严峻的器官功能限制（肾功能不全）制定了综合诊疗方案。

---

## 1. 执行摘要 (Executive Summary)

:::exec-summary
患者: 70岁男性，乙状结肠中分化腺癌 IV期 (ypT4aN2aM1)
关键分子特征: KRAS G12C (11.5%), ATM 胚系突变, TMB-High (79 mut/Mb), MSS
当前治疗: 氟泽雷赛 (Fulzerasib) + 西妥昔单抗 (2025.10起，五线治疗)
核心建议: 继续当前方案，密切监测肾功能与药物相互作用；后线首选 TAS-102+贝伐珠单抗。
紧急程度: 常规 (密切监测肾毒性)
:::

**Summary**:
患者为晚期结直肠癌多线治疗后，携带罕见的 **KRAS G12C** 突变及 **ATM 胚系突变**。尽管为 MSS 表型，但 TMB 极高（79 mut/Mb），提示潜在的 POLE 突变特征。目前接受的 **氟泽雷赛+西妥昔单抗** 方案符合最佳循证医学证据 [[ref:T1|CodeBreaK 300|https://pubmed.ncbi.nlm.nih.gov/37870536/|Evidence B]]。主要挑战在于患者既往因呋喹替尼导致急性肾损伤，目前 eGFR 仅 ~35-40 mL/min，严重限制了后续临床试验入组及肾毒性药物的使用。

---

## 2. 患者概况 (Patient Profile)

### Demographics
- **Age**: 70 years
- **Sex**: Male
- **ECOG PS**: 1
- **Height/Weight**: 165cm / 66kg

### Cancer Diagnosis
- **Primary Cancer**: 乙状结肠恶性肿瘤
- **Histology**: 中分化腺癌 (Adenocarcinoma)
- **Stage**: IV期 (ypT4aN2aM1)
- **Metastatic Sites**: 双肺多发转移 (最大 2.1×1.5cm)，既往肝转移已切除
- **Date of Diagnosis**: 2022.08 (初诊)

### Comorbidities
- **Renal Impairment**: 肌酐 146 μmol/L (eGFR ~35-40 mL/min)，既往 TKI 相关急性肾损伤
- **Cardiovascular**: 高血压 (硝苯地平)，心脏支架术后 (阿托伐他汀)
- **Metabolic**: 糖尿病 (达格列净，阿卡波糖)

---

## 3. 分子特征 (Molecular Profile)

### 3.1 主要驱动突变

| Gene | Variant | Type | VAF | Frequency (cBioPortal) | CIViC Level | Evidence |
|------|---------|------|-----|------------------------|-------------|----------|
| **KRAS** | **G12C** | SNV | 11.5% | 3-4% in CRC | Level B | [Evidence B] 氟泽雷赛/Sotorasib + Cetuximab |
| **ATM** | **Germline** | SNV | - | 5-7% in CRC | Level C | [Evidence C] PARP Inhibitors (e.g., Olaparib) |

**临床意义解读**:
- **KRAS G12C**: 主要驱动基因。单药 G12C 抑制剂易导致 EGFR 通路反馈性激活，必须联合抗 EGFR 单抗 [[ref:P1|Nature Medicine 2024|https://pubmed.ncbi.nlm.nih.gov/38052910/|Divarasib+Cetuximab]]。
- **ATM 胚系突变**: 提示同源重组修复 (HRR) 缺陷，可能对铂类敏感（一线治疗 PR 已证实）及 PARP 抑制剂敏感。建议直系亲属进行遗传咨询。

### 3.2 免疫治疗标志物
- **MSI/MMR 状态**: **MSS / pMMR** (MLH1+, PMS2+, MSH2+, MSH6+)
- **TMB**: **79 mut/Mb (High)**
  - **异常分析**: MSS 肠癌通常 TMB < 10。此患者呈现 "MSS + Ultra-high TMB"，强烈提示 **POLE/POLD1 核酸外切酶结构域突变**。此类肿瘤虽为 MSS，但因复制校对缺陷导致高突变负荷，通常对免疫治疗有响应 [[ref:P2|Lancet Oncol 2023|https://pubmed.ncbi.nlm.nih.gov/36681091/|POLE mutated CRC]]。
- **PD-L1**: CPS = 3 (22C3)

### 3.3 阴性发现
- **BRAF V600E**: 未检出 (排除 BRAF 抑制剂)
- **HER2**: IHC 0 (排除抗 HER2 治疗)

---

## 4. 治疗史回顾 (Treatment History)

:::timeline
- line: 1线 (新辅助)
  date: 2022.08-2022.12
  regimen: 奥沙利铂+卡培他滨+贝伐珠单抗 (5程)
  response: PR
  type: neoadjuvant
  note: 肿瘤显著缩小

- line: 手术
  date: 2023.01
  regimen: 根治性手术
  response: TRG2
  type: surgery
  note: 切除原发灶+肝转移+淋巴结清扫 (5/19 LN+)

- line: 1线 (辅助)
  date: 2023.03-2023.05
  regimen: 奥沙利铂+卡培他滨 (3程)
  response: -
  type: adjuvant
  note: 术后辅助化疗

- line: 1线 (维持)
  date: 2023.05-2023.08
  regimen: 卡培他滨单药
  response: -
  type: maint
  note: 维持治疗期间发现双肺小结节

- line: 2线
  date: 2023.08-2024.01
  regimen: 伊立替康+亚叶酸钙+5-FU+贝伐珠单抗
  response: SD
  type: pd
  note: 后续卡培他滨维持至2024.06

- line: 3线 (尝试1)
  date: 2024.07
  regimen: 呋喹替尼+信迪利单抗
  response: Toxicity
  type: event
  note: 严重不良反应：急性肾损伤 (AKI) + 肢体水肿

- line: 3线 (尝试2)
  date: 2024.09-2025.02
  regimen: 雷替曲塞+信迪利单抗
  response: SD (缩小)
  type: pd
  note: 病情暂时控制，CEA降低

- line: 4线
  date: 2025.02-2025.10
  regimen: 信迪利单抗+抗肿瘤新抗原mRNA疫苗
  response: PD
  type: pd
  note: 肺转移增大，CEA升高至112

- line: 5线 (当前)
  date: 2025.10-今
  regimen: 氟泽雷赛+西妥昔单抗
  response: 待评估
  type: current
  note: 针对 KRAS G12C 靶向治疗
:::

**Key Observations**:
- **TKI 不耐受**: 呋喹替尼导致严重肾损伤，提示应避免瑞戈非尼等同类药物。
- **化疗敏感性**: 含铂方案 PR，含伊立替康方案 SD，符合 ATM 突变特征。
- **免疫反应**: 三线雷替曲塞+免疫曾获 SD (缩小)，支持高 TMB 带来的免疫原性。

---

## 5. 药物/方案对比 (Regimen Comparison)

### 5.1 方案对比表

| Regimen | Evidence Level | 具体给药剂量 | 肾功能调整 (eGFR 35-40) | ORR | mPFS | Key Toxicities | Status |
|---------|----------------|--------------|------------|-----|------|----------------|--------|
| **氟泽雷赛 + 西妥昔单抗** | **[B]** | 氟泽雷赛: 600mg BID<br>西妥昔: 500mg/m² q2w | 密切监测，暂不减量 | ~30% | 7-9m | 皮疹、腹泻、低镁 | **Current** |
| **TAS-102 + 贝伐珠单抗** | **[A]** | TAS-102: 35mg/m² BID d1-5,8-12<br>贝伐: 5mg/kg q2w | CrCl 30-89 无需调整起始剂量 | ~6% | 5.6m | 骨髓抑制 (G3/4 38%) | **Next Line** |
| **PARP 抑制剂 (奥拉帕利)** | **[C]** | 300mg BID | CrCl 31-50: 减量至 200mg BID | N/A | N/A | 贫血、恶心 | **Trial/Off-label** |

### 5.2 各方案详细说明

#### 方案 1: 氟泽雷赛 (Fulzerasib) + 西妥昔单抗 (Cetuximab)
**证据级别**: [Evidence B] (CodeBreaK 300, KRYSTAL-1)
**治疗定位**: 五线挽救治疗 (当前)
**给药方案**:
- **氟泽雷赛**: 600 mg 口服 BID，持续给药。
- **西妥昔单抗**: 首次 400 mg/m²，随后 250 mg/m² 每周 (或 500 mg/m² 每两周)。
**器官功能调整**:
- 肾功能: 同类药 (Sotorasib) 在轻中度肾损无需调整，但需每2周监测肌酐。
**科学依据**: KRAS G12C 突变会导致 EGFR 信号通路反馈性激活，联合抗 EGFR 单抗可阻断此耐药机制，疗效显著优于单药。

#### 方案 2: TAS-102 + 贝伐珠单抗
**证据级别**: [Evidence A] (SUNLIGHT Trial, NCCN Cat 1)
**治疗定位**: 后线标准治疗
**给药方案**:
- **TAS-102**: 35 mg/m² PO BID, d1-5, d8-12, q28d。
- **贝伐珠单抗**: 5 mg/kg IV, d1, d15, q28d。
**器官功能调整**:
- CrCl 30-89 mL/min: 推荐标准剂量，但需密切监测血液学毒性。
- CrCl <30 mL/min: 禁忌或需极度谨慎。

### 5.3 禁用方案及原因
| 方案 | 禁用原因 | 证据来源 |
|------|----------|----------|
| **瑞戈非尼 / 呋喹替尼** | **既往严重急性肾损伤 (AKI)** | [FDA Label / Clinical History] |
| **顺铂 (Cisplatin)** | **肾功能不全 (eGFR < 60)** | [FDA Label] |

---

## 6. 器官功能与剂量 (Organ Function & Dosing)

### 6.1 当前器官功能
| System | Parameter | Value | Normal Range | Status |
|--------|-----------|-------|--------------|--------|
| **Renal** | **Creatinine** | **146 μmol/L** | 57-97 | ⚠️ **Impaired (CKD 3b)** |
| **Renal** | **eGFR** | **~35-40 mL/min** | >90 | ⚠️ **Critical Constraint** |
| Hepatic | ALT/AST | Normal | <40 | ✓ Normal |
| Hematologic | PLT | Normal | >100 | ✓ Adequate (需关注既往II度减少) |

### 6.2 药物相互作用 (Critical!)
**患者正在服用多种慢病药物，需特别注意 CYP3A4 相互作用**：

| 当前用药 | 风险等级 | 相互作用机制 | 处理建议 |
|----------|----------|--------------|----------|
| **硝苯地平 (Nifedipine)** | ⚠️ 高风险 | CYP3A4 底物。G12C 抑制剂可能增加其浓度，导致低血压。 | 密切监测血压，必要时换用氨氯地平。 |
| **阿托伐他汀 (Atorvastatin)** | ⚠️ 高风险 | CYP3A4 底物。联用增加横纹肌溶解风险。 | **建议换药**：换用瑞舒伐他汀或普伐他汀。 |
| **百令胶囊** | ⚡ 中风险 | 成分复杂，可能增加肾脏负担。 | 建议暂停。 |

### 6.3 肾功能监测计划
- **高风险**: 既往 TKI 相关 AKI 史。
- **监测频率**: 每 2 周查肾功能 (肌酐、尿素氮)。
- **造影剂**: 避免使用含碘造影剂 (CT 增强)，改用 MRI 或平扫 CT。

---

## 7. 治疗路线图 (Treatment Roadmap)

### 7.1 当前推荐方案 (详细)

#### 方案名称: 氟泽雷赛 + 西妥昔单抗
**证据等级**: [Evidence B]
**治疗定位**: 五线治疗

**科学依据**:
针对 KRAS G12C 突变，联合抗 EGFR 治疗可克服反馈性耐药。参考 CodeBreaK 300 研究 [[ref:T2|NCT04793958|https://clinicaltrials.gov/study/NCT04793958|ORR 26-30%, mPFS 5.6-9.6m]]。

**毒性管理**:
| 毒性类型 | 预防措施 | 监测方案 | 处理原则 |
|----------|----------|----------|----------|
| **皮肤毒性** | 预防性使用米诺环素 + 保湿霜 | 每周评估皮疹分级 | G3级暂停西妥昔单抗 |
| **低镁血症** | 输注西妥昔单抗前补镁 | 每4周监测电解质 | 口服或静脉补镁 |
| **肾毒性** | 避免脱水，避免 NSAIDs | 每2周监测肌酐 | 肌酐升高 >1.5x 基线暂停 |

### 7.2 后线选择 (详细排序)
| 优先级 | 方案 | 证据等级 | 适用条件 | 关键数据 |
|--------|------|----------|----------|----------|
| 1 | **TAS-102 + 贝伐珠单抗** | [A] | 肾功能稳定 (CrCl >30) | mOS 10.8m (SUNLIGHT) |
| 2 | **PARP 抑制剂 (试验)** | [C] | ATM 突变，PS 良好 | 篮子试验数据 |
| 3 | **双免疫 (CTLA-4+PD-1)** | [C] | 确认 TMB-High (79) | 针对 POLE 突变假设 |

### 7.3 治疗决策流程图

:::roadmap
- title: 当前方案 (五线)
  status: current
  regimen: 氟泽雷赛 + 西妥昔单抗
  actions:
    - 每2周监测肾功能
    - 调整降压药/他汀类药物
    - 预防皮疹

- title: 若有效 (PR/SD)
  status: success
  regimen: 维持治疗
  actions:
    - 持续直至进展或毒性不耐受
    - 考虑对寡转移灶行 SBRT

- title: 若进展 (PD)
  status: danger
  regimen: TAS-102 + 贝伐珠单抗
  actions:
    - 优先考虑临床试验 (PARPi)
    - 启动 TAS-102 (需关注骨髓毒性)
    - 避免使用瑞戈非尼
:::

---

## 8. 分子复查建议 (Re-biopsy / Liquid Biopsy)

**Timing**: 疾病进展 (PD) 时。
**Method**: 液体活检 (ctDNA)，因肺部病灶穿刺风险及肾功能限制造影引导。
**Targets**:
1.  **KRAS G12C 二次突变**: 如 Y96D, G12D/V 等。
2.  **MET 扩增**: 常见的 EGFR 阻断耐药机制，可能提示需加用 MET 抑制剂。
3.  **TMB 复核**: 再次确认 TMB 是否仍为高水平 (79 mut/Mb)，以指导免疫再挑战。

---

## 9. 临床试验推荐 (Clinical Trials)

**重要提示**: 患者 **eGFR ~35-40 mL/min** 是入组的最大障碍。大多数 I 期试验要求 eGFR > 60。以下推荐需仔细核对肾功能入组标准。

### 推荐试验列表 (完整复制自 Recruiter 报告)

#### 试验 1: [NCT05288205] - Glecirasib 联合 JAB-3312
- **NCT 编号**: NCT05288205
- **试验名称**: JAB-21822 (KRAS G12C抑制剂) 联合 JAB-3312 (SHP2抑制剂) 治疗晚期实体瘤
- **试验分期**: Phase I/II
- **研究药物**: Glecirasib + SHP2抑制剂
- **靶点/适应症**: KRAS G12C 突变
- **招募状态**: Recruiting
- **研究中心**: 北京协和医院、中国医科院肿瘤医院
- **匹配原因**: SHP2 抑制剂可能克服 G12C 抑制剂的适应性耐药。
- **入组关键条件**: 既往标准治疗失败；需确认是否允许既往接受过 G12C 抑制剂。
- **可行性**: **? 需确认** (需严格评估肾功能是否符合入组标准)。

#### 试验 2: [NCT06819215] - VB15010 在晚期实体瘤中的研究
- **NCT 编号**: NCT06819215
- **试验名称**: VB15010 (PARP抑制剂) 在晚期实体瘤中的 I/II 期研究
- **试验分期**: Phase I/II
- **研究药物**: VB15010 (PARPi)
- **靶点/适应症**: HRR 基因突变 (含 ATM)
- **招募状态**: Recruiting
- **研究中心**: 山东省肿瘤医院
- **匹配原因**: 针对 ATM 胚系突变，利用合成致死机制。
- **可行性**: **✓ 潜在符合** (PARP 抑制剂肾毒性相对较小，但需确认入组线)。

#### 试验 3: [NCT05123482] - AZD8205 单药或联合
- **NCT 编号**: NCT05123482
- **试验名称**: AZD8205 (PARP1 选择性抑制剂) 单药或联合抗癌药物治疗晚期实体瘤
- **试验分期**: Phase I/II
- **研究药物**: AZD8205
- **靶点/适应症**: HRR 突变
- **招募状态**: Recruiting
- **研究中心**: 北京、长沙、重庆多中心
- **匹配原因**: 新一代 PARP1 选择性抑制剂，毒性可能更低。
- **可行性**: **? 需筛选** (需确认是否开放结直肠癌队列)。

#### 试验 4: [NCT06293014] - TAS-102 联合贝伐珠单抗
- **NCT 编号**: NCT06293014
- **试验名称**: TAS-102 联合贝伐珠单抗二线维持/后线治疗
- **试验分期**: Phase II
- **研究药物**: TAS-102 + Bevacizumab
- **靶点/适应症**: 晚期结直肠癌
- **招募状态**: Recruiting
- **研究中心**: 河南肿瘤医院
- **匹配原因**: 符合 NCCN 指南推荐的后线方案，试验可能提供药物支持。
- **可行性**: **✓ 较符合** (TAS-102 在轻中度肾损中可使用)。

#### 试验 5: [NCT06614192] - ABBV-400 对比 TAS-102
- **NCT 编号**: NCT06614192
- **试验名称**: ABBV-400 (c-Met ADC) 对比 TAS-102 治疗晚期结直肠癌
- **试验分期**: Phase III
- **研究药物**: ABBV-400 vs TAS-102
- **靶点/适应症**: c-Met 过表达
- **招募状态**: Recruiting
- **研究中心**: 多中心 (需查询)
- **匹配原因**: 若 c-Met 高表达可考虑 ADC 药物。
- **可行性**: **? 需测 c-Met**。

#### 试验 6: [NCT05985109] - KN046 联合瑞戈非尼
- **NCT 编号**: NCT05985109
- **研究药物**: KN046 (PD-L1/CTLA-4 双抗) + Regorafenib
- **可行性**: **! 慎重** (瑞戈非尼有肾毒性风险，需极低剂量起始；双抗可能对高 TMB 有效)。

---

## 10. 局部治疗建议 (Local Therapy)

**Current Status**: 双肺多发转移，最大 2.1cm。
**Recommendation**:
- 目前以全身治疗为主。
- **Oligoprogression (寡进展)**: 若全身控制良好，仅个别肺结节增大，可考虑 **SBRT (立体定向放疗)**。
- **Symptomatic**: 若出现咯血或阻塞性肺炎，考虑姑息性放疗。
- **Renal Protection**: 任何局部治疗（如增强 CT 引导的介入）均需避免使用碘造影剂。

---

## 11. 核心建议汇总 (Core Recommendations)

### Recommended Treatment Plan
1.  **Immediate (Current)**: **Fulzerasib 600mg BID + Cetuximab** - **[Evidence B]**
    - **Rationale**: 针对 KRAS G12C 的最佳生物学方案。
    - **Safety Action**: 停用阿托伐他汀/百令胶囊，监测硝苯地平影响；每2周查肌酐。

2.  **Next Line (At Progression)**: **TAS-102 + Bevacizumab** - **[Evidence A]**
    - **Rationale**: SUNLIGHT 研究证实生存获益，且在肾功能不全患者中相对安全。

3.  **Alternative (Trial)**: **PARP Inhibitor** (Targeting ATM) - **[Evidence C]**
    - **Rationale**: 合成致死机制，需筛选允许 eGFR ~40 的试验。

### Not Recommended (Critical!)
**DO NOT USE**:
1.  ❌ **Fruquintinib / Regorafenib**: 既往导致严重急性肾损伤，再次使用风险极高。
2.  ❌ **Cisplatin**: 绝对禁忌 (eGFR < 60)。
3.  ❌ **Single Agent G12C Inhibitor**: 无效，必须联合抗 EGFR。

---

## 12. 参考文献 (References)

1.  [PMID: 37870536 - CodeBreaK 300 Trial](https://pubmed.ncbi.nlm.nih.gov/37870536/) (Sotorasib + Panitumumab in CRC)
2.  [PMID: 38052910 - Divarasib Study](https://pubmed.ncbi.nlm.nih.gov/38052910/) (G12C inhibitor + Cetuximab)
3.  [PMID: 37133585 - SUNLIGHT Trial](https://pubmed.ncbi.nlm.nih.gov/37133585/) (TAS-102 + Bevacizumab)
4.  [PMID: 36681091 - POLE Mutated CRC](https://pubmed.ncbi.nlm.nih.gov/36681091/) (High TMB in MSS CRC)
5.  [PMID: 37852034 - PARP Inhibitors in ATM](https://pubmed.ncbi.nlm.nih.gov/37852034/)
6.  [FDA Label - LONSURF](https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/207981s008lbl.pdf) (TAS-102 Dosing in Renal Impairment)
7.  [[1]](#ref-nct-nct05288205) (Glecirasib Trial)
8.  [[2]](#ref-nct-nct06293014) (TAS-102 + Bev Trial)

---

## References

<a id="ref-nct-nct05288205"></a>**[1]** [NCT: NCT05288205](https://clinicaltrials.gov/study/NCT05288205)

<a id="ref-nct-nct06293014"></a>**[2]** [NCT: NCT06293014](https://clinicaltrials.gov/study/NCT06293014)
