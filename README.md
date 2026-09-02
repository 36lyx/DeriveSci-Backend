# DeriveSci.com 后端

欢迎来到 [DeriveSci](https://derivesci.com)，我是 LYX。

我编篡此集，旨在探讨理科难题，提升推理能力，与广大数学爱好者同飨逻辑之美。

非常欢迎各位访问我的网站，祝各位学有所获，不断精进。

网站草创之初，很多题目没有上传，一些页面没有实现，敬请谅解。

## 新 repo 摘要

先前，[DeriveSci 项目](https://github.com/Louis-Liu-one/DeriveSci) 使用 Flask 后端直接渲染 Jinja2 模板，前后端未分离。随着开发推进，遇到了诸多项目基本结构上的问题。

近日，为了项目持续发展，作者计划从 Flask+Jinja2 模式转为后端 Flask、前端 Vue+NaiveUI 实现前后端分离的模式，目前正在持续开发。

本 repo 为 DeriveSci 项目正在进行重写的后端部分，其中 `models.py` 数据库部分、`fpevaluator.py`、`anschecker.py` 求值引擎无变化，路由处理部分大幅度变化，尤其是处理用户登录态的部分。

**请不要再向已废弃的旧 [DeriveSci 项目](https://github.com/Louis-Liu-one/DeriveSci) 提交 Pull Requests。**
