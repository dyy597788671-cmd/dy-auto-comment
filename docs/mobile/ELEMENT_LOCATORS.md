# 抖音元素定位规则

N为expected_author转换后的XPath字符串字面量，S为current_section转换后的XPath字符串字面量，k为同名候选序号，从1开始。$nickname替换为N，$section替换为S。字符串含两种引号时用concat拼接。查询使用当前phone_device的前台页面。

## L01 启动执行实例

流程步骤：F07至F10

锚点：手机连接信息、系统用户空间ID与包名。

节点关系：实例键为物理设备标识＋系统用户空间ID＋com.ss.android.ugc.aweme。主副实例共享物理连接，按实例键选择启动目标，并核对前台实例所属空间。

读取或操作：调用现有手机连接及系统启动能力；该操作不通过页面元素或resource-id区分主副实例。

## L02 识别首页推荐

流程步骤：F11

锚点：文字“推荐”，以及其祖先的描述“已选中，推荐，按钮”。

节点关系：推荐文字必须位于已选中的推荐标签内。分享面板中的同名“推荐”不具有这一祖先描述。

```xpath
//*[@text='推荐' and ancestor::*[@content-desc='已选中，推荐，按钮']]
```

读取或操作：查询是否存在；存在即结束推荐页初始化，不点击该标签。

## L03 首页搜索入口

流程步骤：F12

锚点：content-desc精确等于“搜索”，且可点击。

节点关系：存在嵌套的同名搜索节点时，取没有同名可点击祖先的外层入口。

```xpath
//*[@content-desc='搜索' and @clickable='true'][not(ancestor::*[@content-desc='搜索' and @clickable='true'])]
```

读取或操作：取得入口节点后单击一次。

## L04 搜索输入框

流程步骤：F13

锚点：搜索输入页面的android.widget.EditText。

节点关系：先取focused=true的输入框；没有焦点输入框时，仅在该页面只有一个EditText时取它。作品页“搜你想看的”TextView不作为可编辑输入框。

```xpath
//android.widget.EditText[@focused="true"] | //android.widget.EditText[not(//android.widget.EditText[@focused="true"]) and count(//android.widget.EditText)=1]
```

读取或操作：输入task_data["keyword"]。该查询只在已进入搜索输入页面后执行。

## L05 搜索按钮

流程步骤：F13

锚点：text精确等于“搜索”，控件为TextView或Button。

节点关系：使用按钮自身文字，不固定输入关键词或父级ID。

```xpath
//*[@text='搜索' and (self::android.widget.TextView or self::android.widget.Button)]
```

读取或操作：取得搜索文字节点后单击一次。

## L06 顶部栏目横向滚动条

流程步骤：F14及F16

锚点：HorizontalScrollView内包含ActionBar.Tab。

节点关系：以栏目Tab识别横向滚动条，读取该节点bounds，不依赖页面根节点路径。

```xpath
//android.widget.HorizontalScrollView[.//androidx.appcompat.app.ActionBar.Tab]
```

读取或操作：从bounds取得left、top、right、bottom。y=(top+bottom)//2；x20=left+(right-left)*20//100；x80=left+(right-left)*80//100。左滑从(x80,y)到(x20,y)，右滑反向。

## L07 综合视频图文栏目

流程步骤：F15至F17

锚点：栏目Tab下text精确等于current_section。

节点关系：只在ActionBar.Tab中的Button或TextView匹配栏目名。图文、视频、综合使用同一条参数化规则。

```xpath
//androidx.appcompat.app.ActionBar.Tab//*[@text=$section and (self::android.widget.Button or self::android.widget.TextView)]
```

读取或操作：将$section替换为S；等待目标出现后点击。未出现时按L06滑动栏目条。

## L08 筛选入口

流程步骤：F18

锚点：content-desc精确等于“筛选，按钮”。

节点关系：描述节点本身可点击时取自身；不可点击时取最近的可点击祖先。

```xpath
//*[@content-desc="筛选，按钮"]/ancestor-or-self::*[@clickable="true"][1]
```

读取或操作：点击取得的动作节点，打开筛选面板。

## L09 筛选一天内

流程步骤：F19

锚点：OCR识别文字精确等于“一天内”。

节点关系：对筛选面板截图执行影刀离线OCR，使用完整结果；文字检测框过滤阈值0.5、检测框大小2。

读取或操作：筛选item["text"].strip()=="一天内"；中心点x=(box[0]+box[2])//2，y=(box[1]+box[3])//2，单击该点。

## L10 筛选查看结果

流程步骤：F19

锚点：OCR识别文字精确等于“查看结果”。

节点关系：使用同一筛选面板OCR结果，按按钮文字区分；不点击“最新发布”。

读取或操作：筛选item["text"].strip()=="查看结果"；按识别框中心点单击。

## L11 传统结构作者昵称

流程步骤：F21及F22

锚点：作者行中包含“喜欢”功能描述的局部节点。

节点关系：找到直接包含点赞操作LinearLayout的作者行；取该行内不可点击LinearLayout的第一个TextView。排除可点击的点赞数量节点。

```xpath
//android.widget.LinearLayout[android.widget.LinearLayout[contains(@content-desc,"喜欢")]]/android.widget.LinearLayout[@clickable="false"]/android.widget.TextView[1]
```

读取或操作：记作A_old。批量读取每个匹配节点的text，并保留节点顺序与卡片关系。

## L12 Compose结构作者昵称

流程步骤：F21及F22

锚点：ComposeView内的作者TextView及其紧邻前方的头像组。

节点关系：作者文字的前一个兄弟节点为不可点击View，内部含两个直接View子节点。按头像组与昵称的局部关系识别，不固定昵称index。

```xpath
//androidx.compose.ui.platform.ComposeView//android.widget.TextView[preceding-sibling::*[1][self::android.view.View and @clickable="false" and count(android.view.View)=2]]
```

读取或操作：记作A_compose。视频和图文分别出现的index=5、index=3不写入定位条件；读取每个匹配节点text。

## L13 按昵称关联当前候选封面

流程步骤：F22及F23

锚点：当前候选昵称节点的精确文字及其所在卡片。

节点关系：按A_old与A_compose获得昵称节点，精确匹配N，并按同名候选序号k选定一个昵称节点，再从该节点查找自己的封面。

读取或操作：传统结构：沿LinearLayout祖先向上取第一个只含一个“FrameLayout／ViewGroup／可点击View”封面的节点，再取该封面。Compose结构：取昵称直接父View内的第一个可点击直接View子节点。封面列表不与独立昵称列表按全屏索引配对。

传统结构相对封面路径R_old

```xpath
ancestor::android.widget.LinearLayout[count(.//android.widget.FrameLayout/android.view.ViewGroup/android.view.View[@clickable="true"])=1][1]//android.widget.FrameLayout/android.view.ViewGroup/android.view.View[@clickable="true"]
```

Compose结构相对封面路径R_compose

```xpath
parent::android.view.View[@clickable="true"]/android.view.View[@clickable="true"][1]
```

当前同名候选昵称路径A及对应封面路径：

```python
A = "(" + A_old + "[@text=" + N + "] | " + A_compose + "[@text=" + N + "])[" + str(k) + "]"
cover_xpath = A + "/" + R_old + " | " + A + "/" + R_compose
```

两分支从同一个候选昵称A出发，按全局同名序号选定候选，再定位自己卡片的封面。

## L14 图文作者头像

流程步骤：F24

锚点：作品作者栏内text精确等于当前作者昵称的文字节点。

节点关系：从作者昵称的直接父节点中，查找可点击ImageView，与昵称保持同一作者栏。

```xpath
//*[@text=$nickname]/parent::*/android.widget.ImageView[@clickable='true']
```

读取或操作：将$nickname替换为N，点击关联头像，进入作者主页。

## L15 视频作者头像

流程步骤：F24

锚点：ImageView的content-desc精确等于当前作者昵称，且可点击。

节点关系：直接用头像自身的作者描述，匹配当前候选作者。

```xpath
//android.widget.ImageView[@clickable='true' and @content-desc=$nickname]
```

读取或操作：将$nickname替换为N，点击头像。

## L16 主页抖音号

流程步骤：F25及F26

锚点：text以“抖音号：”或“抖音号:”开头。

节点关系：匹配抖音号文字节点自身，不依赖昵称下方的公共父容器。认证说明不作为抖音号。

```xpath
//*[starts-with(@text,'抖音号：') or starts-with(@text,'抖音号:')]
```

读取或操作：显式等待该节点，最长3秒，出现即继续。读取text，保存profile_douyin_id_raw，交原verify_author处理。超时仍不存在时沿用原核验出口，不从认证文字拼造抖音号。

## L17 主页作者昵称

流程步骤：F25

锚点：content-desc包含“复制名字和修改备注”。

节点关系：由昵称节点自己的功能描述识别，再读取该节点text；不固定实际昵称。

```xpath
//*[contains(@content-desc,'复制名字和修改备注')]
```

读取或操作：读取text，保存profile_author_name_raw。

## L18 结果区域是否停止变化

流程步骤：F31及F32

锚点：当前结果卡片内的标题、作者昵称等稳定文本；没有有效节点文本时使用截图OCR。

节点关系：复用L11、L12获得的作者节点，沿L13的同卡片关系取得各自结果卡片。仅收集可见结果卡片的标题和作者等内容文本，排除顶部栏目、系统栏、点赞数量及相对时间等动态文字。返回列表后刷新快照，翻页后取新快照。

读取或操作：按屏幕卡片顺序组织各卡片的文本，保留卡片边界及重复项，去除文本内部空白，生成result_content_signature；不把全屏TextView直接拼接。仅当结果区域没有有效节点文本时，沿用离线OCR完整结果、阈值0.5和检测框大小2，保留顶部栏目中线以下的非空文字，去空白排序后生成OCR签名。签名包含来源node或ocr，来源切换时重置连续计数；与上一签名相同则计数加1，不同归零。连续无变化计数达到3，结束本栏目。

## L19 作品点赞

流程步骤：F36

锚点：可点击节点的描述包含“喜欢”和“按钮”。

节点关系：视频和图文共用此规则；匹配作品操作按钮自身描述，点赞状态和数量均不写死。

```xpath
//*[@clickable='true' and contains(@content-desc,'喜欢') and contains(@content-desc,'按钮')]
```

读取或操作：单击一次，然后记录Like。

## L21 视频评论入口

流程步骤：F37

锚点：可点击节点的描述以“评论”开头，且包含“按钮”。

节点关系：父子节点都描述同一评论动作时，排除具有同名可点击祖先的内层节点，取外层动作入口。

```xpath
//*[@clickable='true' and starts-with(@content-desc,'评论') and contains(@content-desc,'按钮')][not(ancestor::*[@clickable='true' and starts-with(@content-desc,'评论') and contains(@content-desc,'按钮')])]
```

读取或操作：单击一次打开评论区。

## L22 视频评论输入框

流程步骤：F38

锚点：评论页面的EditText及focused属性。

节点关系：先取当前有焦点的EditText；没有有焦点输入框时，仅在页面只有一个EditText时取它。同一提示文字的两个输入框用焦点区分。

```xpath
//android.widget.EditText[@focused="true"] | //android.widget.EditText[not(//android.widget.EditText[@focused="true"]) and count(//android.widget.EditText)=1]
```

读取或操作：点击输入框取得焦点，随后向当前光标位置输入已分配评论。图文分支保留原光标输入，不新增这次点击。

## L23 评论发送按钮

流程步骤：F40及F47

锚点：text精确等于“发送”，控件为TextView或Button。

节点关系：在评论输入状态匹配发送文字节点；与分享确认的OCR发送分开使用。

```xpath
//*[@text='发送' and (self::android.widget.TextView or self::android.widget.Button)]
```

读取或操作：点击一次；指令正常返回后记录Comment。视频随后回退一次，图文不回退。

## L24 图文评论入口及原位置检查

流程步骤：F42至F45

锚点：原作品操作栏的“评论”描述及同栏的喜欢、收藏、分享操作。

节点关系：评论节点的直接父ViewGroup须同时有喜欢、收藏、分享的直接LinearLayout子节点。以该四功能操作栏及其中评论按钮的位置复查，不关联上方评论区。

```xpath
//*[@clickable='true' and starts-with(@content-desc,'评论') and contains(@content-desc,'按钮')][parent::android.view.ViewGroup[android.widget.LinearLayout[contains(@content-desc,'喜欢')] and android.widget.LinearLayout[contains(@content-desc,'收藏')] and android.widget.LinearLayout[starts-with(@content-desc,'分享')]]]
```

读取或操作：第一次直接点击；内部两轮重复执行此定位，仅在原操作栏中的评论按钮仍存在时再次点击。评论区上方出现的其它评论节点不满足该操作栏关系。原按钮消失即退出重试；最多三次总点击。

## L25 作品收藏

流程步骤：F49

锚点：可点击节点的描述包含“收藏”和“按钮”。

节点关系：视频和图文共用此规则；匹配收藏动作自身的描述，不固定“未选中／已选中”及收藏数量。

```xpath
//*[@clickable='true' and contains(@content-desc,'收藏') and contains(@content-desc,'按钮')]
```

读取或操作：单击一次，然后记录Favorite。

## L27 作品分享

流程步骤：F50

锚点：可点击节点的描述以“分享”开头，且包含“按钮”。

节点关系：视频和图文共用此规则；匹配作品分享动作，不固定分享数量。

```xpath
//*[@clickable='true' and starts-with(@content-desc,'分享') and contains(@content-desc,'按钮')]
```

读取或操作：单击一次打开分享面板。

## L29 分享上排第一个好友头像

流程步骤：F51

锚点：好友卡片中ImageView的非空描述与TextView的非空文字相同。

节点关系：限定为RecyclerView的直接ViewGroup好友卡片，并保留头像描述与昵称文字一致的关系；在全部合格头像中取第一个。首位规则只作用于好友列表，不对全屏ImageView取第一个。

```xpath
(//androidx.recyclerview.widget.RecyclerView/android.view.ViewGroup[android.widget.ImageView[@content-desc!='']/@content-desc=android.widget.TextView[@text!='']/@text]/android.widget.ImageView[@clickable='true'])[1]
```

读取或操作：点击首位头像一次；不固定好友昵称，不使用固定头像ID。

## L30 分享确认发送

流程步骤：F52

锚点：选择好友后截图中的OCR文字“发送”。

节点关系：使用影刀离线OCR读取该状态截图，精确筛选“发送”；只用于定位发送位置。

读取或操作：取“发送”识别框中心点，单击一次。点击指令正常返回后记录Share，再等待5至10秒。
