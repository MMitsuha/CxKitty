from openai import OpenAI

from cxapi.schema import QuestionModel
from logger import Logger

from . import SearcherBase, SearcherResp


class OpenAISearcher(SearcherBase):
    """ChatGPT 在线答题器 (Responses API)"""

    client: OpenAI
    config: dict

    def __init__(self, **config) -> None:
        super().__init__()
        self.config = config
        self.client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
        self.logger = Logger("OpenAISearcher")

    def invoke(self, question: QuestionModel) -> SearcherResp:
        # 将选项从JSON转换成人类(GPT)易读形式
        options_str = ""
        if type(question.options) is not None:
            options_str = "选项：\n"
            if type(question.options) is dict:
                for k, v in question.options.items():
                    options_str += k + ". " + v + ";"
            elif type(question.options) is list:
                for v in question.options:
                    options_str += v + ";"

        user_content = str(self.config["prompt"]).format(
            type=question.type.name,
            value=question.value,
            options=options_str,
        )
        self.logger.info("从 " + self.config["prompt"] + " 生成提问：" + user_content)

        try:
            stream = self.client.responses.create(
                model=self.config["model"],
                temperature=0.5,  # 答题场景适合把temperature调低
                instructions=self.config["system_prompt"],
                input=[
                    {
                        "role": "user",
                        "content": str(self.config["prompt"]).format(
                            type="单选题",
                            value="We didn’t have health____________ at the time and when I got a "
                            "third infection, my parents couldn’t pay for the treatment.",
                            options="选项：\nA. assurance;B. insurance;C. requirement;D. issure;",
                        ),
                    },  # 这里给个单选题回复示例供 AI 模仿
                    {"role": "assistant", "content": "A. insurance"},
                    {"role": "user", "content": user_content},
                ],
                stream=True,
            )

            # 从流式事件中收集完整文本
            response = ""
            for event in stream:
                if event.type == "response.output_text.delta":
                    response += event.delta
            if not response:
                response = ""
        except Exception as err:
            return SearcherResp(-500, err.__str__(), self, question.value, None)

        # 单选题需要进一步预处理AI返回结果，以使 QuestionResolver 能正确命中
        if question.type.value is 0:
            response = response.strip()
            for k, v in question.options.items():
                # 以 A. 开头、或者包含选项文本
                if response.startswith(k + ".") or (v in response):
                    response = v
                    break
        # 多选同理
        if question.type.value is 1:
            awa = ""
            for k, v in question.options.items():
                if v in response:
                    awa += v + "#"
            response = awa

        self.logger.info("返回结果：" + response)
        return SearcherResp(0, "", self, question.value, response)
