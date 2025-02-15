# 📝 docullim

[![Latest](https://img.shields.io/pypi/v/docullim)](https://pypi.org/project/docullim/#history)
[![Python Versions](https://img.shields.io/pypi/pyversions/docullim)](https://pypi.org/project/docullim/)

auto-generate documentation for python code using llms.

[![asciicast](https://asciinema.org/a/702627.svg)](https://asciinema.org/a/702627)

## ⚙️ installation

```sh
pip install docullim
```

```sh
poetry add docullim
```

## 💻 usage

add `@docullim` to the function or class you want to generate documention for. you can also pass a tag to the annotation like `@docullim("custom_tag")`.

```python
from docullim import docullim

@docullim
def add(a, b):
    return a + b

@docullim("custom_tag")
def sub(a, b):
    return a - b

```

```sh
docullim file1.py file2.py
docullim "src/**/*.py"
docullim --config docullim.json --model gpt-4 "src/**/*.py"
docullim --reset-cache --concurrency 3 --write file1.py "src/**/*.py"
```

config file is a json file that can have `model` as string, `max_concurrency` as number or `prompts` as string pairs.

`docullim.json`

```json
{
  "model": "gpt-4",
  "max_concurrency": 5,
  "prompts": {
    "default": "Generate short and simple documentation explaing the code and include sample usage.",
    "custom_tag": "this is a a diffrent propmt being passed to the llm when @docullim('custom_tag') is passed"
  }
}
```

you should provide your llm api key provided as environment variable by default it requires `OPENAI_API_KEY`.
you can switch models and provide other llm api keys. See [supported llms](https://docs.litellm.ai/docs/providers)

## 🛠️ development

Install the following tools are needed to have this project running

- [devbox](https://www.jetify.com/devbox) manages all the packages needed by the project
- [direnv](https://direnv.net/) loads env variables and run devbox when in project directory

also rename `.env.example` to `.env` and add your llm api key.
