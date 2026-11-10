# Ontology-Workspace

面向企业项目交付人员的本体工具工作台。**只开发工具**，不制作制造业场景模拟、案例数据或业务金标。

语义后端使用固定版本的 Semantica，通过企业 SemanticBackend 适配层隔离上游对象、异常和 API 变化。前端使用 React/TypeScript 完全自建；项目治理、认证、验证、联合发布与部署由工作台提供。

## 开发状态

项目正在从零实施，当前建立 A0/P0 技术基线。此说明不代表后续产品功能已经完成；实际能力以运行证据、测试和门禁为准。Fake Backend 仅用于测试，不用于真实运行或发布。

## 计划

- [设计](docs/superpowers/specs/2026-11-10-ontology-workspace-design.md)
- [A0/P0 实施计划](docs/superpowers/plans/2026-11-10-ontology-workspace-a0.md)
- [P0–P8 总路线](docs/superpowers/plans/2026-11-10-ontology-workspace-roadmap.md)
- [执行进度](docs/progress/a0.md)

## 基线测试

使用 Python 3.12，不能使用本机可能指向旧版本的 `python3`。

```bash
python3.12 -m unittest discover -s tests/bootstrap -v
```

依赖安装、真实 Semantica 探针和产品运行命令将在对应任务实测后加入。开发环境与运行制品保存在被 Git 忽略的目录中。凭据不得进入源码、日志或发布包。
