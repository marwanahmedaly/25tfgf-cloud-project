# Project Resource Guide_ Model Selection, Tooling, and Fine-Tuning



## Page 1

CISC 886 - Cloud Computing
Project Resource Guide: Model Selection, Tooling, and Fine-
Tuning
School of Computing, Queen's University, Kingston, Canada
Overview
This resource may be helpful while you are exploring ideas and doing research for your project,
especially if you are comparing open-source large language models and related tools. The goal is to
help you choose a realistic model, use the right tools, and avoid hardware choices that make fine-tuning
unnecessarily difficult.
1. Choose an Open-Source Model Under 10B Parameters
For this project, you should look for an open-source model with fewer than 10 billion parameters.
Why this matters:
Smaller models are more realistic to fine-tune on free Google Colab or on a modest GPU
instance.
Lower-parameter models need less VRAM, which reduces memory errors during training.
They are faster to train, faster to test, and easier to iterate on when you are still exploring ideas.
If you choose a very large model too early, you may spend more time fighting hardware limitations
than learning from the fine-tuning process.
Why sub-10B models fit free Colab
Free Colab sessions usually give you limited GPU memory and limited runtime. A smaller base model
makes it much more likely that you can complete experiments in a single session, especially when you
combine:
quantized weights
PEFT methods such as LoRA or QLoRA
short training runs for exploration rather than full production tuning
1 / 6

## Page 2

Queen's University CISC 886 - Cloud Computing
This is why starting small is usually the better decision.
2. Prefer PEFT Instead of Full Fine-Tuning
When possible, you should use PEFT (Parameter-Efficient Fine-Tuning) rather than full fine-tuning.
PEFT is a family of methods that updates only a small portion of the model during training instead of
changing every model weight.
Why PEFT is usually the better choice for this project:
It needs much less GPU memory than full fine-tuning.
It trains faster, which is important when you are using Colab or limited cloud resources.
It produces smaller adapter files, which are easier to store and move around.
It lets you keep the original base model unchanged and reuse it for different experiments.
In practice, this means you can explore more ideas with less cost and less setup friction.
3. Where You Can Find Models
You can explore models from several places. Each source is useful for a slightly different reason.
Unsloth
Unsloth is useful when you want an efficient fine-tuning workflow, especially in Colab.
Why it is helpful:
It is designed to make fine-tuning more efficient.
It works well for PEFT-based workflows.
It is especially convenient if your next step is to use the model with Ollama, because you can
export to GGUF format more easily.
If your goal is to fine-tune and then test the result in Ollama, Unsloth is one of the most practical
starting points.
2 / 6

## Page 3

Queen's University CISC 886 - Cloud Computing
Hugging Face
Hugging Face is one of the main places to browse open-source base models and datasets.
You can use it to:
search for base models under 10B parameters
check model licenses and documentation
look for GGUF versions of models
upload a fine-tuned GGUF model after training with Unsloth
If a model is not already available in GGUF format, you may still fine-tune it with Unsloth and then
export the result to GGUF later.
Ollama
Ollama is useful for quickly checking which models are already packaged for local use.
You can use it to:
see what models are already available in the Ollama ecosystem
quickly test models on your local machine
run a model from the terminal using commands such as:
ollama run model-name
This is a fast way to compare models before you invest time in fine-tuning.
4. Prefer Quantized Models When Appropriate
When you are testing or fine-tuning within limited hardware, you should strongly consider using a
quantized model.
Quantization reduces the memory required to store and run the model by using lower-precision
weights.
3 / 6

## Page 4

Queen's University CISC 886 - Cloud Computing
Why quantized models are useful:
They use less VRAM.
They are often easier to run on consumer GPUs or free Colab GPUs.
They make local testing more practical.
They reduce the barrier to trying several models before choosing one.
5. Machine Selection
For models below 10B parameters, you can often work with a machine that has around 16 GB of
VRAM.
Examples:
Google Colab T4 for accessible experimentation
AWS g4dn.xlarge for cloud-based testing and deployment work
These machines are not unlimited, but they are often enough for:
testing smaller open-source models
running quantized models
performing PEFT-based fine-tuning
If you try to use a larger model or a full fine-tuning workflow, you will likely need significantly more
memory and a more expensive machine.
6. Important Tools
Ollama
Ollama is a tool for running large language models locally or on a server through a simple interface.
Why it is useful:
It makes model execution straightforward.
It is convenient for testing models quickly.
4 / 6

## Page 5

Queen's University CISC 886 - Cloud Computing
It works well when your final deployment goal is to serve a model from your own machine or
cloud instance.
It supports workflows that use GGUF models.
In this project context, Ollama acts as the model-serving layer.
OpenWebUI
OpenWebUI is a browser-based user interface for interacting with language models.
Why it matters:
It gives you a simple chat interface in the browser.
It works well with Ollama.
It helps you test prompts and compare responses without building your own frontend from
scratch.
In this project context, Ollama serves the model and OpenWebUI provides the interface you use to
interact with it.
7. Recommended Starting Workflow
If you are not sure where to begin, use this order:
1. Choose an open-source model under 10B parameters.
2. Check whether it is available on Hugging Face, Unsloth, or Ollama.
3. Prefer a quantized version if you want easier local or Colab-based testing.
4. Use PEFT rather than full fine-tuning unless you have a strong reason not to.
5. Fine-tune the model in Google Colab using Unsloth.
6. Export the result to GGUF if you want to use it with Ollama.
7. Test the model through Ollama and, if needed, interact with it through OpenWebUI.
This workflow keeps your exploration realistic, affordable, and easier to debug.
8. Hands-On Resource
5 / 6

## Page 6

Queen's University CISC 886 - Cloud Computing
For a practical starting point, use this Unsloth tutorial:
https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/tutorial-how-to-finetune-llama-3-and-use-in-
ollama
This guide is especially useful if you want hands-on experience with:
fine-tuning in Colab
PEFT-style workflows
exporting to GGUF
testing the result with Ollama
Key Takeaway
For this project, a strong starting strategy is to choose a small open-source model, prefer PEFT, use
quantization when appropriate, fine-tune with Unsloth, and test the result with Ollama and
OpenWebUI. This approach is much more practical than starting with a large model and full fine-
tuning on limited hardware.
6 / 6