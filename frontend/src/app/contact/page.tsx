'use client';

import { useState } from 'react';

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: 'general',
    message: ''
  });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In a real app, this would send to an API
    console.log('Contact form submitted:', formData);
    setSubmitted(true);
  };

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Page Header */}
      <div className="text-center max-w-2xl mx-auto">
        <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">Contact Us</h1>
        <p className="text-white/50">
          Have questions, feedback, or need support? We'd love to hear from you.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {/* Contact Methods */}
        <div className="space-y-4">
          <div className="glass-card p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--gold-muted)] flex items-center justify-center">
                <span className="text-xl">📧</span>
              </div>
              <div>
                <h3 className="font-medium text-white">Email</h3>
                <p className="text-sm text-white/50">Get a response within 24 hours</p>
              </div>
            </div>
            <a href="mailto:support@aquaforge.ai" className="text-[var(--gold-400)] hover:underline">
              support@aquaforge.ai
            </a>
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--gold-muted)] flex items-center justify-center">
                <span className="text-xl">📚</span>
              </div>
              <div>
                <h3 className="font-medium text-white">Documentation</h3>
                <p className="text-sm text-white/50">Guides and tutorials</p>
              </div>
            </div>
            <p className="text-white/60 text-sm">Coming soon</p>
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--gold-muted)] flex items-center justify-center">
                <span className="text-xl">💬</span>
              </div>
              <div>
                <h3 className="font-medium text-white">Community</h3>
                <p className="text-sm text-white/50">Join swim coaches using AquaForge</p>
              </div>
            </div>
            <p className="text-white/60 text-sm">Coming soon</p>
          </div>
        </div>

        {/* Contact Form */}
        <div className="lg:col-span-2">
          <div className="glass-card p-6">
            {submitted ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--success-muted)] flex items-center justify-center">
                  <span className="text-3xl">✓</span>
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">Message Sent!</h3>
                <p className="text-white/50 mb-6">
                  Thank you for reaching out. We'll get back to you soon.
                </p>
                <button
                  onClick={() => {
                    setSubmitted(false);
                    setFormData({ name: '', email: '', subject: 'general', message: '' });
                  }}
                  className="btn btn-outline"
                >
                  Send Another Message
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-white/60 mb-2">Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="input"
                      placeholder="Your name"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-white/60 mb-2">Email</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="input"
                      placeholder="you@example.com"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-white/60 mb-2">Subject</label>
                  <select
                    value={formData.subject}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    className="input"
                  >
                    <option value="general">General Inquiry</option>
                    <option value="support">Technical Support</option>
                    <option value="feature">Feature Request</option>
                    <option value="bug">Bug Report</option>
                    <option value="partnership">Partnership</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-white/60 mb-2">Message</label>
                  <textarea
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    className="input min-h-[150px] resize-none"
                    placeholder="How can we help?"
                    required
                  />
                </div>

                <button type="submit" className="btn btn-gold w-full">
                  Send Message
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
