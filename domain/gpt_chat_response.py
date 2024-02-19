from dataclasses import dataclass
from typing import Any, List, TypeVar, Type, cast, Callable


T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


@dataclass
class Message:
    content: str
    role: str

    @staticmethod
    def from_dict(obj: Any) -> 'Message':
        assert isinstance(obj, dict)
        content = from_str(obj.get("content"))
        role = from_str(obj.get("role"))
        return Message(content, role)

    def to_dict(self) -> dict:
        result: dict = {}
        result["content"] = from_str(self.content)
        result["role"] = from_str(self.role)
        return result


@dataclass
class Choice:
    finish_reason: str
    index: int
    message: Message

    @staticmethod
    def from_dict(obj: Any) -> 'Choice':
        assert isinstance(obj, dict)
        finish_reason = from_str(obj.get("finish_reason"))
        index = from_int(obj.get("index"))
        message = Message.from_dict(obj.get("message"))
        return Choice(finish_reason, index, message)

    def to_dict(self) -> dict:
        result: dict = {}
        result["finish_reason"] = from_str(self.finish_reason)
        result["index"] = from_int(self.index)
        result["message"] = to_class(Message, self.message)
        return result


@dataclass
class Usage:
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int

    @staticmethod
    def from_dict(obj: Any) -> 'Usage':
        assert isinstance(obj, dict)
        completion_tokens = from_int(obj.get("completion_tokens"))
        prompt_tokens = from_int(obj.get("prompt_tokens"))
        total_tokens = from_int(obj.get("total_tokens"))
        return Usage(completion_tokens, prompt_tokens, total_tokens)

    def to_dict(self) -> dict:
        result: dict = {}
        result["completion_tokens"] = from_int(self.completion_tokens)
        result["prompt_tokens"] = from_int(self.prompt_tokens)
        result["total_tokens"] = from_int(self.total_tokens)
        return result


@dataclass
class GPTChatResponse:
    choices: List[Choice]
    created: int
    id: str
    model: str
    object: str
    usage: Usage

    @staticmethod
    def from_dict(obj: Any) -> 'GPTChatResponse':
        assert isinstance(obj, dict)
        choices = from_list(Choice.from_dict, obj.get("choices"))
        created = from_int(obj.get("created"))
        id = from_str(obj.get("id"))
        model = from_str(obj.get("model"))
        object = from_str(obj.get("object"))
        usage = Usage.from_dict(obj.get("usage"))
        return GPTChatResponse(choices, created, id, model, object, usage)

    def to_dict(self) -> dict:
        result: dict = {}
        result["choices"] = from_list(
            lambda x: to_class(Choice, x), self.choices)
        result["created"] = from_int(self.created)
        result["id"] = from_str(self.id)
        result["model"] = from_str(self.model)
        result["object"] = from_str(self.object)
        result["usage"] = to_class(Usage, self.usage)
        return result


def gpt_chat_response_from_dict(s: Any) -> GPTChatResponse:
    return GPTChatResponse.from_dict(s)


def gpt_chat_response_to_dict(x: GPTChatResponse) -> Any:
    return to_class(GPTChatResponse, x)
