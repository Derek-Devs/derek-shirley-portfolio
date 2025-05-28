// src/components/sections/contact/ContactForm.tsx
"use client";

import React, { useState } from 'react';

export default function ContactForm() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: ''
  });
  const [status, setStatus] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const encode = (data: { [key: string]: string }) => {
    return Object.keys(data)
      .map(key => encodeURIComponent(key) + "=" + encodeURIComponent(data[key]))
      .join("&");
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus('Sending...');

    // Determine the path of the current page. For client components, window.location.pathname can be used.
    // However, for the initial POST for Netlify Forms, it's often simplest to use
    // the path where the form is intended to be found by Netlify, or just "/".
    // If your form is on "/contact", you might use "/contact" here.
    // For now, let's stick with "/" if it's generally worked for discovery before,
    // or change it if you know the specific page path (e.g. '/contact')
    const formPostUrl = "/"; // Or specific path like window.location.pathname or "/contact"

    try {
      await fetch(formPostUrl, { // Using a variable for clarity, can keep as "/"
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: encode({
          "form-name": "contact", // This matches the form's name attribute
          ...formData
        })
      });
      setStatus('Message sent successfully!');
      setFormData({ name: '', email: '', message: '' }); // Reset form
    } catch (error) {
      console.error('Form submission error:', error);
      setStatus('Error sending message. Please try again.');
    }

    setTimeout(() => setStatus(''), 5000); // Clear status after 5 seconds
  };

  return (
    <div className="w-full">
      <h2 className="text-2xl font-semibold mb-6 text-base-content">Send me a message</h2>
      <form
        name="contact" 
        method="POST" 
        action="/thank-you" 
        data-netlify="true" 
        netlify-honeypot="bot-field"
        onSubmit={handleSubmit}
        className="space-y-4"
      >

        <input type="hidden" name="form-name" value="contact" />
        

        <p className="hidden">
          <label>
            Don’t fill this out if you’re human: <input name="bot-field" onChange={handleChange} />
          </label>
        </p>

        <div>
          <label htmlFor="name" className="block text-sm font-medium text-base-content/80 mb-1">
            Your Name
          </label>
          <input
            type="text"
            id="name"
            name="name"
            required
            value={formData.name}
            onChange={handleChange}
            className="input input-bordered w-full bg-base-100"
            placeholder="Jane Doe"
            disabled={status === 'Sending...'}
          />
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-base-content/80 mb-1">
            Your Email
          </label>
          <input
            type="email"
            id="email"
            name="email"
            required
            value={formData.email}
            onChange={handleChange}
            className="input input-bordered w-full bg-base-100"
            placeholder="jane.doe@example.com"
            disabled={status === 'Sending...'}
          />
        </div>

        <div>
          <label htmlFor="message" className="block text-sm font-medium text-base-content/80 mb-1">
            Message
          </label>
          <textarea
            id="message"
            name="message"
            rows={5}
            required
            value={formData.message}
            onChange={handleChange}
            className="textarea textarea-bordered w-full bg-base-100"
            placeholder="How can I help you?"
            disabled={status === 'Sending...'}
          />
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pt-2">
          <button
            type="submit"
            className="btn btn-primary w-full sm:w-auto"
            disabled={status === 'Sending...'}
          >
            {status === 'Sending...' ? (
              <>
                <span className="loading loading-spinner loading-xs"></span>
                Sending...
              </>
            ) : (
              'Send Message'
            )}
          </button>

          {status && status !== 'Sending...' && (
              <p className={`text-sm text-right ${status.includes('Error') ? 'text-error' : 'text-success'}`}>
                {status}
              </p>
          )}
        </div>
      </form>
    </div>
  );
}