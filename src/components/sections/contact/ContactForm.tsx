"use client";

import React from 'react';

export default function ContactForm() {
  return (
    <div className="w-full">
      <h2 className="text-2xl font-semibold mb-6 text-base-content">Send me a message</h2>
      <form
        name="contact"
        method="POST"
        action="/thank-you"
        data-netlify="true"
        netlify-honeypot="bot-field"
        className="space-y-4"
      >
        <input type="hidden" name="form-name" value="contact" />
        
        <p className="hidden">
          <label>
            Do not fill this out if you are human: <input name="bot-field" />
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
            className="input input-bordered w-full bg-base-100"
            placeholder="Jane Doe"
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
            className="input input-bordered w-full bg-base-100"
            placeholder="jane.doe@example.com"
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
            className="textarea textarea-bordered w-full bg-base-100"
            placeholder="Let us talk about a data challenge, a specific project, or a potential opportunity..."
          />
        </div>

        <div className="pt-2">
          <button
            type="submit"
            className="btn btn-primary w-full sm:w-auto"
          >
            Send Message
          </button>
        </div>
      </form>
    </div>
  );
}