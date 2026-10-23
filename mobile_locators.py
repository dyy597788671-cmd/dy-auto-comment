"""已确认方案的集中定位；只生成XPath，不连接或操作手机。

依据：docs/mobile/locator_plan.json。手机SDK与OCR调用由mobile_adapter负责。
本模块仅使用Python标准库，可整体放入现有应用的xbot_robot目录。
"""

APP_PACKAGE = "com.ss.android.ugc.aweme"

# L20、L26、L28已分别合并到L19、L25、L27，不再建立重复定义。
LOCATOR_IDS = ("L01", "L02", "L03", "L04", "L05", "L06", "L07", "L08", "L09", "L10", "L11", "L12", "L13", "L14", "L15", "L16", "L17", "L18", "L19", "L21", "L22", "L23", "L24", "L25", "L27", "L29", "L30",)

XPATHS = {
    "L02": "//*[@text='推荐' and ancestor::*[@content-desc='已选中，推荐，按钮']]",
    "L03": "//*[@content-desc='搜索' and @clickable='true'][not(ancestor::*[@content-desc='搜索' and @clickable='true'])]",
    "L04": "//android.widget.EditText[@focused=\"true\"] | //android.widget.EditText[not(//android.widget.EditText[@focused=\"true\"]) and count(//android.widget.EditText)=1]",
    "L05": "//*[@text='搜索' and (self::android.widget.TextView or self::android.widget.Button)]",
    "L06": "//android.widget.HorizontalScrollView[.//androidx.appcompat.app.ActionBar.Tab]",
    "L07": "//androidx.appcompat.app.ActionBar.Tab//*[@text=$section and (self::android.widget.Button or self::android.widget.TextView)]",
    "L08": "//*[@content-desc=\"筛选，按钮\"]/ancestor-or-self::*[@clickable=\"true\"][1]",
    "L11": "//android.widget.LinearLayout[android.widget.LinearLayout[contains(@content-desc,\"喜欢\")]]/android.widget.LinearLayout[@clickable=\"false\"]/android.widget.TextView[1]",
    "L12": "//androidx.compose.ui.platform.ComposeView//android.widget.TextView[preceding-sibling::*[1][self::android.view.View and @clickable=\"false\" and count(android.view.View)=2]]",
    "L14": "//*[@text=$nickname]/parent::*/android.widget.ImageView[@clickable='true']",
    "L15": "//android.widget.ImageView[@clickable='true' and @content-desc=$nickname]",
    "L16": "//*[starts-with(@text,'抖音号：') or starts-with(@text,'抖音号:')]",
    "L17": "//*[contains(@content-desc,'复制名字和修改备注')]",
    "L19": "//*[@clickable='true' and contains(@content-desc,'喜欢') and contains(@content-desc,'按钮')]",
    "L21": "//*[@clickable='true' and starts-with(@content-desc,'评论') and contains(@content-desc,'按钮')][not(ancestor::*[@clickable='true' and starts-with(@content-desc,'评论') and contains(@content-desc,'按钮')])]",
    "L22": "//android.widget.EditText[@focused=\"true\"] | //android.widget.EditText[not(//android.widget.EditText[@focused=\"true\"]) and count(//android.widget.EditText)=1]",
    "L23": "//*[@text='发送' and (self::android.widget.TextView or self::android.widget.Button)]",
    "L24": "//*[@clickable='true' and starts-with(@content-desc,'评论') and contains(@content-desc,'按钮')][parent::android.view.ViewGroup[android.widget.LinearLayout[contains(@content-desc,'喜欢')] and android.widget.LinearLayout[contains(@content-desc,'收藏')] and android.widget.LinearLayout[starts-with(@content-desc,'分享')]]]",
    "L25": "//*[@clickable='true' and contains(@content-desc,'收藏') and contains(@content-desc,'按钮')]",
    "L27": "//*[@clickable='true' and starts-with(@content-desc,'分享') and contains(@content-desc,'按钮')]",
    "L29": "(//androidx.recyclerview.widget.RecyclerView/android.view.ViewGroup[android.widget.ImageView[@content-desc!='']/@content-desc=android.widget.TextView[@text!='']/@text]/android.widget.ImageView[@clickable='true'])[1]",
}

OCR_TEXT = {"L09": "一天内", "L10": "查看结果", "L30": "发送"}

NATIVE_RELATIVE_COVER_XPATH = "ancestor::android.widget.LinearLayout[count(.//android.widget.FrameLayout/android.view.ViewGroup/android.view.View[@clickable=\"true\"])=1][1]//android.widget.FrameLayout/android.view.ViewGroup/android.view.View[@clickable=\"true\"]"
COMPOSE_RELATIVE_COVER_XPATH = "parent::android.view.View[@clickable=\"true\"]/android.view.View[@clickable=\"true\"][1]"

# 结果卡片与封面使用同一作者起点，不用两个全屏列表按序号配对。
NATIVE_RELATIVE_CARD_XPATH = NATIVE_RELATIVE_COVER_XPATH.rsplit(
    "//android.widget.FrameLayout", 1
)[0]
COMPOSE_RELATIVE_CARD_XPATH = 'parent::android.view.View[@clickable="true"]'


def xpath_literal(value):
    """把完整原文编码成XPath 1.0字面量，包含两种引号时使用concat。"""
    if not isinstance(value, str):
        raise TypeError("XPath字面量必须是字符串")
    if "'" not in value:
        return "'" + value + "'"
    if '"' not in value:
        return '"' + value + '"'
    return "concat(" + ', "\'", '.join("'" + part + "'" for part in value.split("'")) + ")"


def _author_path(expected_author, occurrence):
    if not isinstance(expected_author, str) or not expected_author:
        raise ValueError("expected_author必须是非空昵称")
    if isinstance(occurrence, bool) or not isinstance(occurrence, int) or occurrence < 1:
        raise ValueError("occurrence必须是从1开始的整数")
    name = xpath_literal(expected_author)
    # 先对两类作者取联合，再取全局第k个；不分别对每一分支取第k个。
    return (
        "(" + XPATHS["L11"] + "[@text=" + name + "] | "
        + XPATHS["L12"] + "[@text=" + name + "])["
        + str(occurrence) + "]"
    )


def build_author_cover_xpath(expected_author, occurrence=1):
    """L13：保留已确认的合法联合表达式及全局同名序号。"""
    author = _author_path(expected_author, occurrence)
    return (
        author + "/" + NATIVE_RELATIVE_COVER_XPATH + " | "
        + author + "/" + COMPOSE_RELATIVE_COVER_XPATH
    )


def build_author_card_xpath(expected_author, occurrence=1):
    """L18：从当前候选作者取得同一卡片，供快照提取稳定内容。"""
    author = _author_path(expected_author, occurrence)
    return (
        author + "/" + NATIVE_RELATIVE_CARD_XPATH + " | "
        + author + "/" + COMPOSE_RELATIVE_CARD_XPATH
    )


def get_xpath(locator_id, nickname=None, section=None, occurrence=1):
    """返回本次完整XPath；实例、OCR和签名不伪装成元素查询。"""
    if locator_id == "L13":
        return build_author_cover_xpath(nickname, occurrence)
    if locator_id not in XPATHS:
        if locator_id not in LOCATOR_IDS:
            raise KeyError("未知定位编号：" + str(locator_id))
        raise ValueError(locator_id + "通过实例、OCR或卡片签名处理，不是固定XPath")
    expression = XPATHS[locator_id]
    def replace_parameter(match):
        name = match.group(1)
        value = {"nickname": nickname, "section": section}[name]
        if not isinstance(value, str) or not value:
            raise ValueError(locator_id + "需要" + name)
        return xpath_literal(value)

    # 单次替换模板变量；昵称里的$section等文字必须保持原文。
    import re
    return re.sub(r"\$(nickname|section)\b", replace_parameter, expression)
