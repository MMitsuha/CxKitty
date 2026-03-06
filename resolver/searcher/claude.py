from anthropic import Anthropic

from cxapi.schema import QuestionModel
from logger import Logger

from . import SearcherBase, SearcherResp


class ClaudeSearcher(SearcherBase):
    """Claude 在线答题器"""

    client: Anthropic
    config: dict

    def __init__(self, **config) -> None:
        super().__init__()
        self.config = config
        client_kwargs = {"api_key": config["api_key"]}
        if "base_url" in config:
            client_kwargs["base_url"] = config["base_url"]
        self.client = Anthropic(**client_kwargs)
        self.logger = Logger("ClaudeSearcher")

    def invoke(self, question: QuestionModel) -> SearcherResp:
        # 将选项从JSON转换成人类易读形式
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
            message = self.client.messages.create(
                model=self.config["model"],
                max_tokens=1024,
                temperature=0.5,
                system=self.config["system_prompt"],
                messages=[
                    {
                        "role": "user",
                        "content": str(self.config["prompt"]).format(
                            type="单选题",
                            value="We didn't have health____________ at the time and when I got a "
                            "third infection, my parents couldn't pay for the treatment.",
                            options="选项：\nA. assurance;B. insurance;C. requirement;D. issure;",
                        ),
                    },
                    {"role": "assistant", "content": "A. insurance"},
                    {"role": "user", "content": user_content},
                ],
            )

            response = message.content[0].text
            if response is None:
                response = ""
        except Exception as err:
            return SearcherResp(-500, err.__str__(), self, question.value, None)

        # 单选题需要进一步预处理AI返回结果，以使 QuestionResolver 能正确命中
        if question.type.value is 0:
            response = response.strip()
            for k, v in question.options.items():
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
