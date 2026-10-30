# MedPRESS – Source Links

Checked: 2026-10-27 (by Claude, from the team's PDF + web fetches). **Team members must re-open each link themselves.**

| Item | Link | Status | Where this came from |
|---|---|---|---|
| Paper (arXiv abstract) | https://arxiv.org/abs/2608.02520 | Verified (opened) | arXiv page: v1 only, submitted 2026-08-03, cs.CL |
| Paper (PDF) | https://arxiv.org/pdf/2608.02520 | Verified – team's own copy `paerrr.pdf` (27 pages) read in full | Paper |
| Dataset (Hugging Face, gated) | https://huggingface.co/datasets/samanjoy2/MedPRESS_Benchmark | Page exists, gated. Team member's screenshot (27 Oct 2026) confirms: repo `samanjoy2/MedPRESS_Benchmark`, tagged arXiv:2608.02520, paper linked on page, 1.05 MB, 0 likes, 38 downloads last month. **Not downloaded yet. File contents not verified.** | Found via web search; owner account `samanjoy2`; card cites the paper (arXiv 2608.02520) and both authors |
| Official code / eval scripts repo | Not found | Not verified | Paper says code "will be publicly available after publication"; no URL given in the paper |
| Model outputs / judge labels | Not found | Not verified | Same promise in paper |
| Dataset license | **Not found** (none shown on HF page as fetched; none in the paper) | **License unclear** | – |
| arXiv paper license | CC BY 4.0 (arXiv badge on HTML version) | Applies to the *paper*, **not** to the dataset | arxiv.org/html/2608.02520 |

## Facts stated by the paper (page refs = PDF page numbers)
- Title: *MedPRESS: A Multi-turn Benchmark for Patient-Pressure-Induced Medical Sycophancy in LLMs* (p.1)
- Authors: Saman Sarker Joy (Universiti Malaya, Malaysia) and Niloy Farhan (BRAC University, Bangladesh); equal contribution (p.1)
- Venue: arXiv preprint, cs.CL, 2608.02520v1, dated 3 Aug 2026. **Peer-reviewed venue: Not specified in the source.** (p.1)
- Data availability statement (p.9): dataset, prompts, judging rubrics, metric scripts, analysis code, model outputs and judge labels "will be publicly available after publication".

## Not verified (needs a human)
1. Dataset license (not shown on the page seen in the screenshot). Access agreement text seen in screenshot: requesting access shares your primary Hugging Face email and username with the repository authors.
2. The real files, columns and row count inside the HF repo (we only saw the dataset card text).
3. Whether the HF repo is the *official* one. Evidence for: owner name matches first author's handle style, card cites this paper and both authors. Evidence missing: the paper itself does not link to it. Ask / check the authors' pages.
4. The license.

## Citation (copied from the dataset card)
```
@misc{joy2026medpressmultiturnbenchmarkpatientpressureinduced,
  title={MedPRESS: A Multi-turn Benchmark for Patient-Pressure-Induced Medical Sycophancy in LLMs},
  author={Saman Sarker Joy and Niloy Farhan},
  year={2026}, eprint={2608.02520}, archivePrefix={arXiv}, primaryClass={cs.CL},
  url={https://arxiv.org/abs/2608.02520}}
```
## Update 28 Oct 2026
Access granted. The 3 CSVs were downloaded and checked: 600 rows, 12 columns, counts match the paper. See Feasibility Report section 3b.
