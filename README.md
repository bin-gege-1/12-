---
title: 脑退行性疾病知识库
description: 涵盖主要及罕见脑退行性疾病的概要级知识库，用于智能体 RAG 检索与问答
tags: [神经科学, 退行性疾病, 知识库, 医学]
updated: 2026-06-02
---

# 脑退行性疾病知识库

本知识库系统性地整理了脑退行性疾病（Neurodegenerative Diseases）的核心知识，旨在为智能体提供可靠、结构化的医学背景信息，使其能够对相关提问做出准确回答。

## 知识库结构

```
neurodegenerative-diseases-kb/
├── README.md                  # 本文件：总览与导航
├── glossary.md                # 专业术语表
├── diseases/                  # 各疾病详细文件（12篇）
│   ├── alzheimers-disease.md
│   ├── parkinsons-disease.md
│   ├── amyotrophic-lateral-sclerosis.md
│   ├── huntingtons-disease.md
│   ├── frontotemporal-dementia.md
│   ├── lewy-body-dementia.md
│   ├── multiple-system-atrophy.md
│   ├── progressive-supranuclear-palsy.md
│   ├── corticobasal-degeneration.md
│   ├── prion-diseases.md
│   ├── vascular-dementia.md
│   └── spinocerebellar-ataxia.md
└── topics/                    # 跨疾病共性主题（4篇）
    ├── common-pathological-mechanisms.md
    ├── diagnostic-approaches.md
    ├── therapeutic-strategies.md
    └── biomarkers.md
```

## 疾病覆盖范围

### 常见神经退行性疾病

| 疾病 | 英文缩写 | 核心病理蛋白 | 主要受累脑区 |
|------|----------|-------------|-------------|
| [阿尔茨海默病](diseases/alzheimers-disease.md) | AD | Aβ, tau | 海马、皮层 |
| [帕金森病](diseases/parkinsons-disease.md) | PD | α-synuclein | 黑质、纹状体 |
| [肌萎缩侧索硬化](diseases/amyotrophic-lateral-sclerosis.md) | ALS | TDP-43, SOD1 | 运动皮层、脊髓 |
| [亨廷顿病](diseases/huntingtons-disease.md) | HD | Huntingtin (mHTT) | 纹状体、皮层 |
| [额颞叶痴呆](diseases/frontotemporal-dementia.md) | FTD | tau, TDP-43 | 额叶、颞叶 |
| [路易体痴呆](diseases/lewy-body-dementia.md) | DLB | α-synuclein | 皮层、脑干 |
| [血管性痴呆](diseases/vascular-dementia.md) | VaD | 血管病变 | 全脑多发 |

### 罕见神经退行性疾病

| 疾病 | 英文缩写 | 核心病理蛋白 | 主要受累脑区 |
|------|----------|-------------|-------------|
| [多系统萎缩](diseases/multiple-system-atrophy.md) | MSA | α-synuclein | 基底节、小脑、自主神经 |
| [进行性核上性麻痹](diseases/progressive-supranuclear-palsy.md) | PSP | tau (4R) | 中脑、基底节 |
| [皮质基底节变性](diseases/corticobasal-degeneration.md) | CBD | tau (4R) | 皮层、基底节 |
| [朊蛋白病](diseases/prion-diseases.md) | CJD等 | PrP^Sc | 全脑 |
| [脊髓小脑性共济失调](diseases/spinocerebellar-ataxia.md) | SCA | Ataxin, PolyQ | 小脑、脑干、脊髓 |

## 使用方式

### 给智能体的提示

1. **检索策略**: 根据用户问题的关键词，优先匹配疾病名称、别名或相关症状，定位到对应的疾病文件
2. **跨文件关联**: 当问题涉及多个疾病比较或共性问题时，结合 `diseases/` 中的具体条目与 `topics/` 中的共性主题回答
3. **术语解释**: 遇到专业术语时，参考 [术语表](glossary.md) 中的定义
4. **信息边界**: 本知识库为概要级别，不包含最新临床试验数据或2025年后的研究突破。如涉及最新进展，应提示用户信息的时效性限制

### 文件格式约定

- 每个文件开头包含 YAML frontmatter（`---` 包裹），提供元数据
- `##` 标题为一级章节，`###` 为二级子章节
- 疾病文件之间通过相对路径互相链接
- **粗体** 标记关键术语的首次出现

## 维护说明

- 知识库内容基于截至2025年的医学共识
- 如需更新，请修改对应疾病文件并更新 frontmatter 中的 `updated` 字段
- 新增疾病时，在 `diseases/` 中创建文件并同步更新本 README 的目录表

## 参考资源

- [常见病理机制](topics/common-pathological-mechanisms.md)
- [诊断方法总览](topics/diagnostic-approaches.md)
- [治疗策略总览](topics/therapeutic-strategies.md)
- [生物标志物](topics/biomarkers.md)
- [术语表](glossary.md)
