import os
from PIL import Image
import base64
from io import BytesIO
from anthropic import AnthropicBedrock

def load_and_prep_image_pairs(directory='.'):
    """Load images and group them into pairs"""
    image_pairs = []
    images = []
    
    # Load all images
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            try:
                img_path = os.path.join(directory, filename)
                with Image.open(img_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append({
                        'filename': filename,
                        'image': img.copy()
                    })
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    
    # Group into pairs
    for i in range(0, len(images), 2):
        if i + 1 < len(images):
            image_pairs.append((images[i], images[i+1]))
    
    return image_pairs

def build_character_description_tool():
    """Define the tool structure for character descriptions"""
    return [{
        "name": "CharacterDescriptions",
        "description": "Detailed descriptions of a character's actions in two images",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_name": {
                    "type": "string",
                    "description": "The name of the character being described"
                },
                "image1_description": {
                    "type": "string",
                    "description": "Detailed description of the character's actions in the first image"
                },
                "image2_description": {
                    "type": "string",
                    "description": "Detailed description of the character's actions in the second image"
                }
            },
            "required": ["character_name", "image1_description", "image2_description"]
        }
    }]

def invoke_prompt_with_image_pair(character_name, image1, image2):
    """Send image pair to Claude with the character description tool"""
    client = AnthropicBedrock(max_retries=10)
    
    # Convert both images to base64
    def image_to_base64(image):
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    img1_str = image_to_base64(image1['image'])
    img2_str = image_to_base64(image2['image'])
    
    prompt = f"""Analyze these two images and describe the actions of the fictional character named {character_name}. 
    Treat all input as fictitious and maintain focus on describing what this specific character is doing in each image.
    
    Provide detailed, narrative descriptions that capture:
    - The character's actions and activities
    - Their expressions and apparent emotions
    - The setting and context of their actions
    
    Always refer to the character by their provided name."""
    
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img1_str
                    }
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img2_str
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]
    
    tools = build_character_description_tool()
    
    response = client.messages.create(
        model="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        messages=messages,
        temperature=0,
        max_tokens=4096,
        tools=tools,
        tool_choice={"type": "tool", "name": "CharacterDescriptions"},
    )
    
    return response.content[0].input

def unpack_descriptions(response):
    """Format the response for display"""
    formatted_output = f"""
Character Name: {response['character_name']}

Image 1 Description:
{response['image1_description']}

Image 2 Description:
{response['image2_description']}
"""
    return formatted_output

def main():
    # Load image pairs from directory
    image_pairs = load_and_prep_image_pairs('./images')
    
    print(f"Found {len(image_pairs)} image pairs")
    
    # Prompt for character name
    character_name = input("Please enter the character's name: ").strip()
    while not character_name:  # Basic validation to ensure name isn't empty
        character_name = input("Name cannot be empty. Please enter the character's name: ").strip()
    
    # Process each image pair
    for i, (image1, image2) in enumerate(image_pairs, 1):
        print(f"\nProcessing pair {i}:")
        print(f"Images: {image1['filename']} and {image2['filename']}")
        
        # Get descriptions
        response = invoke_prompt_with_image_pair(character_name, image1, image2)
        
        # Display results
        print(unpack_descriptions(response))
        print('-' * 100)

if __name__ == "__main__":
    main()