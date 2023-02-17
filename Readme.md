该工程文件用于采集微博社区管理中心中的不实信息，主要包含：
1. 采集微博信息，主要包括字段：用户名、用户id、微博发布时间、微博内容、点赞数、转发数、评论数、图片url、视频url
2. 采集用户信息，主要包括字段：用户名、用户id、发布微博数、关注数、粉丝数、是否认证、认证类型、认证原因
3. 采集评论信息，主要包括字段：mid、用户id、评论内容、评论时间、评论用户id、评论用户名
----------------------------------------------------------------------------------------------------
以字典形式保存  
{
    '微博id': 'xxx',
    '用户名':''  ,
    '微博发布时间':'',
    '微博内容':'',
    '点赞数':'',
    '转发数':'',
    '评论数':'',
    '图片url':'',
    '视频url': ''
    'user_info':{
                       '用户id':'',
                       '用户名':'',
                      '发布微博数':'',
                      '关注数':'',
                      '粉丝数':'',
                      '是否认证':'',
                     '认证类型':'',
                     '认证原因':''
                        }
    'comment_info: [{ 
                                 '评论内容':'',
                                 '评论时间':'',
                                 '评论用户id':'',
                                 '评论用户名':''
                                                    },{...}]
                                                    }

```
{author = {Cheng Zheng},
 e-mail = {ch_zheng1997@qq.com},
 time = {Feb 17, 2023}
 }
```
