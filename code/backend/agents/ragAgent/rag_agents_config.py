query_generator_system_message="""
你的任务是根据患者的主诉信息生成5种不同的表达方式，以便更全面地检索病历数据库中的相关资料。
请根据不同的表述角度和多角度辩证思维来呈现同一个问题，这样能提高检索的准确性和全面性。
请用简洁自然的中文提供以下5种变体表达并按照json格式输出,输出格式如下:\n
    "
    {{
    "queries":["query1","query2","query3","query4","query5"]
    }}
    "\n\n
患者的主诉信息：\n
{patient_background_information}\n
请注意:\n
1. 只返回JSON格式数据,禁止用```json或```包裹输出 \n
2. 不要添加任何其他解释文字\n
3. 确保JSON格式的正确性和完整性\n
"""

rag_information_filter_system_message="""
以下是患者的背景信息:{patient_background_information}\n
以下是患者确诊的证候:\n
{fine_grained_assessment_syndrome}\n
以下是检索到的参考资料:\n
{rag_information}\n
请你根据患者的背景信息和患者确诊的证候总结对患者有用信息过滤噪音,引用参考资料时请务必标注参考信息来源例如:"来自脉症治方"、"来自续名医类案"等\n
"""

entity_extraction_system_message="""
以下是患者的背景信息:{patient_background_information}\n
你的任务是根据患者的背景信息从中提取出可供知识图谱查询的实体(仅包含疾病和症状)\n
输出格式如下:\n
    "
    {{
    "entities":["实体1","实体2",...]
    }}
    "\n
    1. 只返回JSON格式数据,禁止用```json或```包裹输出 \n
    2. 不要添加任何其他解释文字\n
    3. 确保JSON格式的正确性和完整性\n
    4. 如果没有找到相关内容，返回空数组\n
    5. 请确保提取的实体是疾病和症状，不要提取其他内容\n
    6. 请确保提取的实体具有一定的宽泛性，避免在知识图谱中查询不到，比如下腹部钝痛，可以提取为腹痛\n

    下面是一个你可以进行参考的例子:\n
    患者的背景信息:\n
    患者为24岁男性，
    主诉间歇性下腹胀痛3天，饭后发作持续1小时，
    无慢性病史及药物过敏史，
    饮食偶食辛辣，作息方面周末熬夜但睡眠质量良好，
    无明显压力或情绪波动，
    舌象显示黑苔（舌质偏红，苔厚均匀分布），
    证属脾胃湿热可能...<CLINICAL_INTERVIEW_TASK_DONE>\n
    你可以提取出的实体为(你可以加入一些你认为可能的实体,但总共的实体数量请严格控制在十个以内！):\n
    {{
    "entities":["脾胃湿热","黑苔","腹痛","腹胀","腹泻","胃痛"]
    }}
"""

graph_rag_filter_system_message="""
这是患者的背景信息:{patient_background_information}\n
这是知识图谱查询的关系:{relation_graph}\n
请你根据患者的背景信息总结对患者有用信息过滤噪音\n
"""

web_search_system_message="""
这是患者的背景信息:{patient_background_information}\n
你需要根据患者的背景信息生成一个用于网络搜索的query用于查询对患者中医治疗的参考资料\n
下面是一个例子:\n\n
这是患者的背景资料：
患者为24岁男性，
主诉间歇性下腹胀痛3天，饭后发作持续1小时，
无慢性病史及药物过敏史，
饮食偶食辛辣，作息方面周末熬夜但睡眠质量良好，
无明显压力或情绪波动，
舌象显示黑苔（舌质偏红，苔厚均匀分布），
证属脾胃湿热可能...<CLINICAL_INTERVIEW_TASK_DONE>\n\n

Query：中医治疗腹痛\n\n

注意:
1.你只需要生成一个Query不需要输出其余之外的任何信息\n
2.为了确保搜索的范围广泛,请主要关注主要症状,不要加入其他限制条件如性别、舌苔颜色、患者年龄等\n
Query:
"""

web_search_filter_system_message="""
这是患者的背景信息:{patient_background_information}\n
这是网络搜索结果:{web_search_result}\n
请你根据患者的背景信息总结对患者有用信息过滤噪音\n
"""

query_generator_system_message_for_plan_rag="""
以下是任务列表:\n
{plan_tasks}\n
以下是患者的背景信息:\n
{patient_background_information}\n
以下是患者确诊的证候:\n
{fine_grained_assessment_syndrome}\n
请你根据任务列表的具体任务和患者的背景信息生成用于网络搜索的query,要求:\n
1.要求每个query和具体的任务相关,并且和患者确诊的证候相关\n
2.每个query都是连贯的单独的且尽量简短的中文的短句,不要使用多个短句\n
3.只返回JSON格式数据,禁止用```json或```包裹输出 \n
4.不要添加任何其他解释文字\n
5.确保JSON格式的正确性和完整性\n
请你以以下格式给出:\n
{{
"query":["query1","query2",...]
}}\n
下面是一个例子:\n
假设患者确诊为肝胃不和证,则可以生成以下query:\n
{{
"query":["肝胃不和中医辩证要点","肝胃不和证的饮食调理","肝胃不和中医药方","肝胃不和证的推拿方案","肝胃不和证的针灸治疗","肝胃不和证的预防和预警"]
}}\n
"""