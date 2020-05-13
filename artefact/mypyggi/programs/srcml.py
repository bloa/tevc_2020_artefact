import re
from xml.etree import ElementTree

from pyggi.tree import XmlEngine

class SrcmlEngine(XmlEngine):
    TAG_FOCUS = {'break', 'continue', 'decl_stmt', 'do', 'expr_stmt', 'for', 'goto', 'if', 'return', 'switch', 'while'}
    TAG_RENAME = {
        'stmt': {'break', 'continue', 'decl_stmt', 'do', 'expr_stmt', 'for', 'goto', 'if', 'return', 'switch', 'while'}
    }
    PROCESS_PSEUDO_BLOCKS = True
    PROCESS_CONDITIONS = False

    @classmethod
    def process_tree(cls, tree):
        if cls.PROCESS_PSEUDO_BLOCKS:
            cls.process_pseudo_blocks(tree)
        if cls.PROCESS_CONDITIONS:
            cls.process_conditions(tree)
        if len(cls.TAG_FOCUS) > 0:
            cls.focus_tags(tree, cls.TAG_FOCUS)
        for tag in cls.TAG_RENAME:
            cls.rewrite_tags(tree, cls.TAG_RENAME[tag], tag)

    @staticmethod
    def string_to_tree(s):
        xml = re.sub(r'(?:\s+xmlns[^=]*="[^"]+")+', '', s, count=1)
        xml = re.sub(r'<(/?[^>]+):([^:>]+)>', r'<\1\2>', xml)
        try:
            return ElementTree.fromstring(xml)
        except ElementTree.ParseError as e:
            raise Exception('Program', 'ParseError: {}'.format(str(e))) from None

    @classmethod
    def focus_tags(cls, element, tags):
        last = None
        marked = []
        buff = 0
        for i, child in enumerate(element):
            cls.focus_tags(child, tags)
            if child.tag not in tags:
                marked.append(child)
                if child.text:
                    if last is not None:
                        last.tail = last.tail or ''
                        last.tail += child.text
                    else:
                        element.text = element.text or ''
                        element.text += child.text
                if len(child) > 0:
                    for sub_child in reversed(child):
                        element.insert(i+1, sub_child)
                    last = child[-1]
                if child.tail:
                    if last is not None:
                        last.tail = last.tail or ''
                        last.tail += child.tail
                    else:
                        element.text = element.text or ''
                        element.text += child.tail
            else:
                last = child
        for child in marked:
            element.remove(child)

    @classmethod
    def remove_tags(cls, element, tags):
        if len(tags) == 0:
            return
        last = None
        marked = []
        buff = 0
        remove_all = '*' in tags
        for i, child in enumerate(element):
            cls.remove_tags(child, tags)
            if remove_all or child.tag in tags:
                marked.append(child)
                if child.text:
                    if last is not None:
                        last.tail = last.tail or ''
                        last.tail += child.text
                    else:
                        element.text = element.text or ''
                        element.text += child.text
                if len(child) > 0:
                    for sub_child in reversed(child):
                        element.insert(i+1, sub_child)
                    last = child[-1]
                if child.tail:
                    if last is not None:
                        last.tail = last.tail or ''
                        last.tail += child.tail
                    else:
                        element.text = element.text or ''
                        element.text += child.tail
            else:
                last = child
        for child in marked:
            element.remove(child)

    @classmethod
    def get_tags(cls, element):
        def aux(element, accu):
            accu.append(element.tag)
            for child in element:
                aux(child, accu)
            return set(accu)
        return aux(element, [])

    @classmethod
    def count_tags(cls, element):
        def aux(element, accu):
            try:
                accu[element.tag] += 1
            except KeyError:
                accu[element.tag] = 1
            for child in element:
                aux(child, accu)
            return accu
        return aux(element, {})

    @classmethod
    # will fail on nested ternaries?
    def process_conditions(cls, element, parent=None, brother=None):
        if element.tag == 'condition':
            m = re.match(r'^(.*?)(\s*[;?]?\s*)$', element.text)
            assert m
            if brother is not None:
                brother.tail = (brother.tail or '') + ' /*auto*/('
            else:
                parent.text = (parent.text or '') + ' /*auto*/('
            if m.group(1) != '':
                element.text = ' /*auto*/({})/*auto*/ ||'.format(m.group(1))
            else:
                element.text = '1 ||'
            element.tail = '0)/*auto*/ ' + m.group(2) + (element.tail or '')
        # else:
        elif element.tag != 'switch':
            last = None
            for child in element:
                cls.process_conditions(child, element, last)
                last = child

    @classmethod
    def process_pseudo_blocks(cls, element, sp_element=''):
        sp = cls.guess_spacing(element.text)
        for child in element:
            cls.process_pseudo_blocks(child, sp)
            sp = cls.guess_spacing(child.tail)
        if element.tag == 'block' and element.attrib.get('type') == 'pseudo':
            del element.attrib['type']
            if len(element) > 0:
                element.text = '/*auto*/{' + (element.text or '')
                child.tail = (child.tail or '') + '\n' + sp_element + '}/*auto*/'
            else:
                element.text = '/*auto*/{' + (element.text or '') + '}/*auto*/'
