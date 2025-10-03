import React from "react";

const categories = [
    { id: 1, name: "Books", description: "All kinds of books" },
    { id: 2, name: "Movies", description: "Latest and classic movies" },
    { id: 3, name: "Music", description: "Albums and singles" },
    { id: 4, name: "Games", description: "Board and video games" },
];

export default function CategoriesPage() {
    return (
        <main style={{ padding: "2rem" }}>
            <h1>Categories</h1>
            <ul style={{ listStyle: "none", padding: 0 }}>
                {categories.map((category) => (
                    <li
                        key={category.id}
                        style={{
                            marginBottom: "1.5rem",
                            padding: "1rem",
                            border: "1px solid #ddd",
                            borderRadius: "8px",
                        }}
                    >
                        <h2 style={{ margin: "0 0 0.5rem 0" }}>{category.name}</h2>
                        <p style={{ margin: 0 }}>{category.description}</p>
                    </li>
                ))}
            </ul>
        </main>
    );
}