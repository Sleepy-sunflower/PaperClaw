---
name: add-spec-tests
description: 按当前 OpenSpec 变更的 Scenario 补测试并运行 pytest。在用户要求补测试、写测试，或实现带 spec 场景的变更时使用。
---

# 按规范补测试

1. 读当前变更里的 `spec.md`，列出每个 Scenario。
2. 为每个 Scenario 写一个测试，名称能对上 Scenario，并标明正常路径、失败路径或边界。
3. 运行 `pytest`。
4. 失败就改实现或改测试，直到退出码为 0。不要删掉 spec 里的失败场景来换通过。
