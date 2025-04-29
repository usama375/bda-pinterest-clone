import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fasthtml import * # FastHTML components
from fasthtml.components import Input # Explicitly import Input if needed elsewhere
from pydantic import BaseModel
from typing import List, Dict, Optional
import os

# --- Application Setup ---
app = FastAPI()

# In-memory storage (replace with database for real app)
users = {} # Store user sign-up info (username: {email, password}) - NOT SECURE for passwords
images = { # Store image details
    1: {"id": 1, "url": "https://via.placeholder.com/300x200.png?text=Image+1", "description": "A lovely placeholder", "likes": 10, "comments": ["Great shot!", "Beautiful."]},
    2: {"id": 2, "url": "https://via.placeholder.com/300x200.png?text=Image+2", "description": "Another placeholder view", "likes": 5, "comments": ["Nice."]},
    3: {"id": 3, "url": "https://via.placeholder.com/300x200.png?text=Image+3", "description": "Placeholder number three", "likes": 22, "comments": []},
    4: {"id": 4, "url": "https://via.placeholder.com/300x200.png?text=Image+4", "description": "Yet another one", "likes": 1, "comments": ["Cool"]},
    5: {"id": 5, "url": "https://via.placeholder.com/300x200.png?text=Image+5", "description": "Placeholder five", "likes": 8, "comments": []},
    6: {"id": 6, "url": "https://via.placeholder.com/300x200.png?text=Image+6", "description": "Number six", "likes": 15, "comments": ["Wow!", "Amazing"]},
}
next_image_id = 7

# --- Helper Functions ---

def render_page(*content, title="Simple UI"):
    """Wraps content in basic HTML structure with HTMX"""
    return HTMLResponse(str(
        Html(
            Head(
                Title(title),
                Meta(charset="utf-8"),
                Meta(name="viewport", content="width=device-width, initial-scale=1"),
                Script(src="https://unpkg.com/htmx.org@1.9.12"), # Include HTMX
                # Basic CSS for layout
                Style("""
                    body { font-family: sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
                    .container { max-width: 900px; margin: auto; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                    .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px; border-bottom: 1px solid #ccc; margin-bottom: 20px; }
                    .header input[type='search'] { flex-grow: 1; margin: 0 15px; padding: 8px; }
                    .header button, .header a { padding: 8px 12px; text-decoration: none; background-color: #eee; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; }
                    .header a { display: inline-block; }
                    .image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
                    .image-grid-item img { max-width: 100%; height: auto; display: block; border: 1px solid #ddd; }
                    .image-detail { display: flex; gap: 20px; }
                    .image-detail img { max-width: 60%; height: auto; object-fit: contain; border: 1px solid #ddd; }
                    .image-info { flex-grow: 1; }
                    .actions button { margin-right: 10px; padding: 5px 10px; }
                    .comments-section { margin-top: 20px; }
                    .comments-list { list-style: none; padding: 0; margin-bottom: 15px; }
                    .comments-list li { padding: 8px; border-bottom: 1px solid #eee; }
                    .comment-form input { width: calc(100% - 80px); padding: 8px; }
                    .comment-form button { padding: 8px 15px; }
                    .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000;}
                    .modal-content { background: white; padding: 30px; border-radius: 5px; min-width: 300px; max-width: 500px; }
                    .hidden { display: none; }
                """)
            ),
            Body(
                Div(*content, Class="container"),
                Div(id="modal-container") # Target for modal content
            )
        )
    ))

# --- Page Endpoints ---

@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    """Page 1: Sign-up Form"""
    form_content = Form(
        H2("Sign Up"),
        P(Label("Username:", fr="username"), Input(type="text", id="username", name="username", required=True)),
        P(Label("Email:", fr="email"), Input(type="email", id="email", name="email", required=True)),
        P(Label("Password:", fr="password"), Input(type="password", id="password", name="password", required=True)),
        Button("Sign Up", type="submit"),
        action="/signup", method="post" # Post to the signup handler
    )
    return render_page(form_content, title="Sign Up")

@app.post("/signup")
async def handle_signup(username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    """Handle sign-up form submission"""
    if username in users:
        # Ideally, return an error message on the form page using HTMX
        raise HTTPException(status_code=400, detail="Username already exists")
    users[username] = {"email": email, "password": password} # NOTE: Store hashed passwords in reality!
    print(f"New user signed up: {username}, {email}")
    # Redirect to the main feed after sign-up
    return RedirectResponse(url="/", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def feed_page():
    """Page 2: Main Feed / Dashboard"""
    header = Div(
        Button("Post", hx_get="/post-form", hx_target="#modal-container", hx_swap="innerHTML"), # Load form into modal
        fasthtml.components.Input(type="search", placeholder="Search", name="q"), # Use explicit import due to name clash
        A("User Profile", href="#"), # Simple link for now
        Class="header"
    )

    image_grid_items = []
    # Sort images by ID descending to show newest first (optional)
    sorted_image_ids = sorted(images.keys(), reverse=True)
    for img_id in sorted_image_ids:
        img_data = images[img_id]
        image_grid_items.append(
            A(
                Img(src=img_data['url'], alt=img_data['description']),
                href=f"/image/{img_id}",
                Class="image-grid-item"
            )
        )

    image_grid = Div(*image_grid_items, Class="image-grid")

    return render_page(header, image_grid, title="Feed")


@app.get("/image/{image_id}", response_class=HTMLResponse)
async def image_detail_page(image_id: int):
    """Page 3: Image Detail View"""
    if image_id not in images:
        raise HTTPException(status_code=404, detail="Image not found")

    img_data = images[image_id]

    # --- Components for HTMX updates ---
    def render_like_section(img_id: int, current_likes: int):
        return Span(
            f"{current_likes} Likes",
            Button("Like", hx_post=f"/like/{img_id}", hx_target=f"#likes-{img_id}", hx_swap="outerHTML"),
            Button("Unlike", hx_post=f"/unlike/{img_id}", hx_target=f"#likes-{img_id}", hx_swap="outerHTML"),
            id=f"likes-{img_id}"
        )

    def render_comments_list(img_id: int, comments: List[str]):
        list_items = [Li(comment) for comment in comments] if comments else [Li("No comments yet.")]
        return Ul(*list_items, id=f"comments-list-{img_id}", Class="comments-list")
    # --- End HTMX Components ---

    image_display = Div(
        Img(src=img_data['url'], alt=img_data['description']),
        Class="image-main"
    )

    image_info = Div(
        H2("Image Details"),
        P(img_data['description']),
        Div(render_like_section(image_id, img_data['likes']), Class="actions"),
        Div(
            H3("Comments"),
            Div(render_comments_list(image_id, img_data['comments'])), # Initial comments list
            Form( # Comment submission form
                Input(type="text", name="comment", placeholder="Add a comment...", required=True),
                Button("Post", type="submit"),
                hx_post=f"/comment/{image_id}",
                hx_target=f"#comments-list-{image_id}", # Target the list for updates
                hx_swap="outerHTML", # Replace the whole list UL
                hx_on="htmx:afterRequest: this.reset()" # Clear form after submit
            ),
            Class="comments-section"
        ),
        Class="image-info"
    )

    content = Div(image_display, image_info, Class="image-detail")
    return render_page(content, title=f"Image {image_id}")

# --- HTMX Action Endpoints ---

@app.post("/like/{image_id}", response_class=HTMLResponse)
async def like_image(image_id: int):
    """Handle HTMX like action"""
    if image_id not in images:
        raise HTTPException(status_code=404, detail="Image not found")
    images[image_id]['likes'] += 1

    # Return the updated like section HTML fragment
    def render_like_section(img_id: int, current_likes: int):
         return Span(
            f"{current_likes} Likes",
            Button("Like", hx_post=f"/like/{img_id}", hx_target=f"#likes-{img_id}", hx_swap="outerHTML"),
            Button("Unlike", hx_post=f"/unlike/{img_id}", hx_target=f"#likes-{img_id}", hx_swap="outerHTML"),
            id=f"likes-{img_id}"
        )
    return HTMLResponse(str(render_like_section(image_id, images[image_id]['likes'])))


@app.post("/unlike/{image_id}", response_class=HTMLResponse)
async def unlike_image(image_id: int):
    """Handle HTMX unlike action"""
    if image_id not in images:
        raise HTTPException(status_code=404, detail="Image not found")
    if images[image_id]['likes'] > 0:
        images[image_id]['likes'] -= 1

    # Return the updated like section HTML fragment
    def render_like_section(img_id: int, current_likes: int):
         return Span(
            f"{current_likes} Likes",
            Button("Like", hx_post=f"/like/{img_id}", hx_target=f"#likes-{img_id}", hx_swap="outerHTML"),
            Button("Unlike", hx_post=f"/unlike/{img_id}", hx_target=f"#likes-{img_id}", hx_swap="outerHTML"),
            id=f"likes-{img_id}"
        )
    return HTMLResponse(str(render_like_section(image_id, images[image_id]['likes'])))


@app.post("/comment/{image_id}", response_class=HTMLResponse)
async def add_comment(image_id: int, comment: str = Form(...)):
    """Handle HTMX comment submission"""
    if image_id not in images:
        raise HTTPException(status_code=404, detail="Image not found")
    if comment: # Add non-empty comments
        images[image_id]['comments'].append(comment)

    # Return the updated comments list HTML fragment
    def render_comments_list(img_id: int, comments: List[str]):
        list_items = [Li(c) for c in comments] if comments else [Li("No comments yet.")]
        return Ul(*list_items, id=f"comments-list-{img_id}", Class="comments-list")

    return HTMLResponse(str(render_comments_list(image_id, images[image_id]['comments'])))


@app.get("/post-form", response_class=HTMLResponse)
async def get_post_form():
    """Return the HTML for the post creation modal form"""
    form_content = Div(
        Div(
            H2("Create New Post"),
            Form(
                P(Label("Choose Image:", fr="image_file"), Input(type="file", id="image_file", name="image_file", accept="image/*", required=True)),
                P(Label("Description:", fr="description"), Textarea(id="description", name="description", rows="4", required=True)),
                Button("Post Image", type="submit"),
                Button("Cancel", type="button", hx_get="/close-modal", hx_target="#modal-container", hx_swap="innerHTML"), # Button to close modal
                action="/upload", method="post", enctype="multipart/form-data",
                # Redirect after successful post using HTMX response header
                hx_on="htmx:afterOnLoad: if(event.detail.xhr.status === 200) window.location.href='/'"
            ),
            Class="modal-content"
        ),
        Class="modal",
        # Optional: click outside modal to close
        # hx_get="/close-modal", hx_target="#modal-container", hx_swap="innerHTML", hx_trigger="click from:body"
    )
    return HTMLResponse(str(form_content))


@app.get("/close-modal", response_class=HTMLResponse)
async def close_modal():
    """Return empty content to effectively close/remove the modal"""
    return HTMLResponse("")


@app.post("/upload")
async def handle_upload(description: str = Form(...), image_file: UploadFile = File(...)):
    """Handle the image upload form submission"""
    global next_image_id
    print(f"Received upload: {image_file.filename}, Description: {description}")

    # --- Simulate saving and adding ---
    # In a real app:
    # 1. Generate a unique filename
    # 2. Save the file: content = await image_file.read(); with open(save_path, "wb") as f: f.write(content)
    # 3. Store file path or URL in the database along with description

    new_id = next_image_id
    images[new_id] = {
        "id": new_id,
        # Use a placeholder, or ideally store and serve the actual uploaded image
        "url": f"https://via.placeholder.com/300x200.png?text=New+Post+{new_id}",
        "description": description,
        "likes": 0,
        "comments": []
    }
    next_image_id += 1

    # Indicate success. The HTMX form handler will trigger a redirect on success (status 200).
    # Alternatively, send an HTMX response header to redirect:
    # return Response(status_code=200, headers={"HX-Redirect": "/"})
    # For simplicity, relying on the hx_on in the form for redirection.
    return HTMLResponse(status_code=200, content="Upload successful")


# --- Run the app (for local development) ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)