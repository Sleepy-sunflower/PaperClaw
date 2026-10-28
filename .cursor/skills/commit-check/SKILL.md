---
name: commit-check
description: 按完成定义检查一次变更能否提交、合并或打版本标签。在用户要求提交、合并、写提交说明、发布、打标签，或确认一次变更是否完成时使用。
---

# 提交检查

一次提交只做当前 OpenSpec 变更里 `tasks.md` 的一个编号分组。还涉及另一个分组时，先拆出去，不继续提交。

下面五条都能勾上才算完成。勾不上的那一条就是未完成的部分。

- 本次 spec 的每个 Scenario 都已满足，包括 `AGENTS.md` 三条硬约束的判据。
- 已运行 `README.md`「测试」一节的命令，退出码为 0。没有使用 `--no-verify`，也没有删除失败用例或放宽断言来换通过。
- 行为有变化时，`README.md`、相关 spec 和 `docs/data-dictionary.md` 已同步。
- 提交说明写明改了什么、依据哪一份 spec，并记下测试退出码、报告路径和 `GET /health` 的结果。
- 提交说明分开写三类检查：人工核对了场景、逐资源授权、迁移能否回滚、提示词的无命中和 arXiv 失败；Harness 核对了 `.cursor/rules/` 与 `AGENTS.md`；代码风格交给格式化工具，不由人工或 Harness 逐行检查。

## 打标签

只在用户要求发布或打标签时继续。提交检查尚未通过时，不启动，也不打标签。

1. 按 `README.md` 复制 `.env.example` 并执行 `docker compose up --build`。
2. 请求 `http://localhost:8000/health`，确认 HTTP 200，且数据库为连通。
3. 任一步失败就停止。修好后从提交检查重新做。
4. 全部通过后，在这次提交上打形如 `v0.0.1` 的 Git 标签。
