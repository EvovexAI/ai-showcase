# -*- coding: utf-8 -*-
import json, os
ROOT = 'D:/dev/github/evo/edu/ai-demos/1006-ai-creative-ad-video'
J = lambda p: json.load(open(os.path.join(ROOT, p), encoding='utf-8'))
chars, scenes, props, shotlist = J('06-spec/characters.json'), J('06-spec/scenes.json'), J('06-spec/props.json'), J('05-meta/shotlist.json')
lines = []
# 1) 人物三视图 x3 —— prompt 取 characters.json 原文，仅画幅词与 CLI 参数(16:9)对齐
for c in chars['characters']:
    p = c['threeview_prompt'].replace('9:16 竖构图', '16:9 横构图')
    lines.append({"asset_id": c['id'], "type": "threeview", "prompt": p, "ratio": "16:9", "resolution": "1K", "ref": [], "out": f"30-assets/{c['id']}/threeview.png"})
# 2) 场景四视图 x5
for s in scenes['scenes']:
    p = s['fourview_prompt'].replace('9:16 竖构图', '16:9 横构图')
    lines.append({"asset_id": s['id'], "type": "fourview", "prompt": p, "ratio": "16:9", "resolution": "1K", "ref": [], "out": f"30-assets/{s['id']}/fourview.png"})
# 3) 道具正视 x3 —— 依据 props.json material/size_ref/continuous_rule + style-lock 红线锚点
prop_prompts = {
 "外卖袋": "产品正视特写，红色无纺布保温外卖袋立于纯浅灰背景前，袋面印红色「饱」字，正面贴白色订单条，袋口半开露出一角红油与餐盒边缘，约30×35cm，无纺布纹理清晰，右上方45°暖主光加左前冷蓝补光，古风写实电影感棚拍质感，无文字水印，16:9 横构图",
 "扫码枪": "产品正视特写，黑色磨砂塑料手持扫码枪立于纯浅灰背景前，长约18cm，红色扇形激光从枪头向画面左侧扫出，塑料磨砂材质细节清晰，右上方45°暖主光加左前冷蓝补光，古风写实电影感棚拍质感，无文字水印，16:9 横构图",
 "二维码": "产品正视特写，一部亮屏智能手机正对镜头立于纯浅灰背景前，屏幕显示清晰的收款二维码：白底黑码、外圈黄色圆角边框，屏幕玻璃带轻微指纹与暖橙灯光反光，二维码清晰可辨不镜像，右上方45°暖主光，古风写实电影感棚拍质感，无文字水印，16:9 横构图",
}
for pid in ["外卖袋", "扫码枪", "二维码"]:
    lines.append({"asset_id": f"props-{pid}", "type": "prop-front", "prompt": prop_prompts[pid], "ratio": "16:9", "resolution": "1K", "ref": [], "out": f"30-assets/props-{pid}/front.png"})
# 4) 首帧 x15 —— image_prompt 取 shotlist 原文，ref 照抄 ref_images
for sh in shotlist['shots']:
    lines.append({"asset_id": sh['shot_id'], "type": "keyframe", "prompt": sh['image_prompt'], "ratio": "9:16", "resolution": "1K", "ref": sh['ref_images'], "out": f"40-keyframes/{sh['shot_id']}.png"})
with open(os.path.join(ROOT, '06-spec', 'image-prompts.jsonl'), 'w', encoding='utf-8') as f:
    for l in lines:
        f.write(json.dumps(l, ensure_ascii=False) + '\n')
print('total lines:', len(lines))
for l in lines:
    print(l['asset_id'], '|', l['type'], '| ref:', len(l['ref']))
