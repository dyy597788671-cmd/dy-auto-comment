"""XPath 1.0语义回归。lxml仅供开发验证，运行模块不依赖它。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mobile_locators as loc

try:
    from lxml import etree
except ImportError:
    etree = None


@unittest.skipIf(etree is None, "开发验证需要lxml")
class MobileLocatorTests(unittest.TestCase):
    def native_card(self, name, marker):
        card = etree.XML("""
        <android.widget.LinearLayout>
          <android.widget.FrameLayout><android.view.ViewGroup>
            <android.view.View clickable="true"/>
          </android.view.ViewGroup></android.widget.FrameLayout>
          <android.widget.LinearLayout>
            <android.widget.LinearLayout clickable="false">
              <android.widget.TextView/><android.widget.TextView text="其他文字"/>
            </android.widget.LinearLayout>
            <android.widget.LinearLayout content-desc="喜欢，12，按钮"/>
          </android.widget.LinearLayout>
        </android.widget.LinearLayout>""")
        card.xpath(".//android.widget.TextView")[0].set("text", name)
        card.xpath(".//android.view.View")[0].set("marker", marker)
        return card

    def compose_card(self, name, marker):
        wrapper = etree.XML("""
        <androidx.compose.ui.platform.ComposeView>
          <android.view.View clickable="true">
            <android.view.View clickable="true"/>
            <android.view.View clickable="false">
              <android.view.View/><android.view.View/>
            </android.view.View>
            <android.widget.TextView/>
          </android.view.View>
        </androidx.compose.ui.platform.ComposeView>""")
        wrapper.xpath(".//android.widget.TextView")[0].set("text", name)
        wrapper.xpath(".//android.view.View[@clickable='true']")[1].set("marker", marker)
        return wrapper

    def test_mixed_structures_use_one_global_occurrence(self):
        name = '同名\'作者"甲'
        for reverse in (False, True):
            tree = etree.XML("<hierarchy><arbitrary><wrapper/></arbitrary></hierarchy>")
            host = tree[0][0]
            cards = [self.native_card(name, "native"), self.compose_card(name, "compose")]
            if reverse:
                cards.reverse()
            for card in cards:
                host.append(card)
            expected = ["compose", "native"] if reverse else ["native", "compose"]
            for k, marker in enumerate(expected, 1):
                selected = tree.xpath(loc.build_author_cover_xpath(name, k))
                self.assertEqual([n.get("marker") for n in selected], [marker])
                card = tree.xpath(loc.build_author_card_xpath(name, k))
                self.assertEqual(len(card), 1)
                self.assertIn(selected[0], list(card[0].iter()))
            self.assertEqual(tree.xpath(loc.build_author_cover_xpath(name, 3)), [])

    def test_literal_round_trips_as_exact_text(self):
        tree = etree.XML("<root/>")
        for value in ("", "普通昵称", "a'b", 'a"b', 'a\'"中', "\'$section\"", "换行\n昵称"):
            self.assertEqual(tree.xpath("string(" + loc.xpath_literal(value) + ")"), value)

    def test_parameter_looking_text_inside_nickname_stays_literal(self):
        tree = etree.XML("<root><author><android.widget.TextView/><android.widget.ImageView clickable='true'/></author></root>")
        name = '作者$section与$nickname\'"'
        tree[0][0].set("text", name)
        self.assertEqual(tree.xpath(loc.get_xpath("L14", nickname=name)), [tree[0][1]])

    def test_first_friend_requires_local_name_relation(self):
        tree = etree.XML("""
        <hierarchy>
          <android.widget.ImageView clickable="true" marker="unrelated"/>
          <androidx.recyclerview.widget.RecyclerView>
            <android.view.ViewGroup>
              <android.widget.ImageView content-desc="头像甲" clickable="true" marker="wrong"/>
              <android.widget.TextView text="别的名字"/>
            </android.view.ViewGroup>
            <android.view.ViewGroup>
              <android.widget.ImageView content-desc="好友乙" clickable="true" marker="first"/>
              <android.widget.TextView text="好友乙"/>
            </android.view.ViewGroup>
            <android.view.ViewGroup>
              <android.widget.ImageView content-desc="好友丙" clickable="true" marker="second"/>
              <android.widget.TextView text="好友丙"/>
            </android.view.ViewGroup>
          </androidx.recyclerview.widget.RecyclerView>
        </hierarchy>""")
        self.assertEqual([n.get("marker") for n in tree.xpath(loc.get_xpath("L29"))], ["first"])

    def test_focused_input_and_unambiguous_fallback(self):
        tree = etree.XML("<root><android.widget.EditText/><android.widget.EditText focused='true'/></root>")
        for key in ("L04", "L22"):
            self.assertEqual(tree.xpath(loc.get_xpath(key)), [tree[1]])
            tree[1].set("focused", "false")
            self.assertEqual(tree.xpath(loc.get_xpath(key)), [])
            tree.remove(tree[1])
            self.assertEqual(tree.xpath(loc.get_xpath(key)), [tree[0]])
            tree.append(etree.Element("android.widget.EditText", focused="true"))

    def test_recommendation_requires_selected_home_tab(self):
        tree = etree.XML("""
        <root>
          <share><android.widget.TextView text="推荐"/></share>
          <tab content-desc="已选中，推荐，按钮"><android.widget.TextView text="推荐"/></tab>
        </root>""")
        self.assertEqual(tree.xpath(loc.get_xpath("L02")), [tree[1][0]])

    def test_all_static_expressions_are_xpath_10_and_id_independent(self):
        for key in loc.XPATHS:
            expression = loc.get_xpath(key, nickname='a\'"', section="图文")
            etree.XPath(expression)
            self.assertNotIn("resource-id", expression)
            self.assertNotIn("/hierarchy/", expression)

    def test_bad_occurrences_and_non_xpath_kinds_are_rejected(self):
        for value in (0, -1, True, 1.0):
            with self.assertRaises(ValueError):
                loc.build_author_cover_xpath("作者", value)
        for key in ("L01", "L09", "L10", "L18", "L30"):
            with self.assertRaises(ValueError):
                loc.get_xpath(key)
        with self.assertRaises(KeyError):
            loc.get_xpath("L20")


if __name__ == "__main__":
    unittest.main()
