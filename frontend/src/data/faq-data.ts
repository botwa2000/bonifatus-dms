// frontend/src/data/faq-data.ts

export enum FAQCategory {
  GETTING_STARTED = 'Getting Started & Features',
  BILLING_SECURITY = 'Billing & Security',
  INTEGRATIONS = 'Integrations & Cloud Storage',
  TROUBLESHOOTING = 'Troubleshooting & Support'
}

export interface FAQ {
  id: string
  category: FAQCategory
  question: string
  answer: string
}

export const faqs: FAQ[] = [
  // ========================================
  // GETTING STARTED & FEATURES (18 questions)
  // ========================================
  {
    id: 'getting-started-1',
    category: FAQCategory.GETTING_STARTED,
    question: 'How do I create an account?',
    answer: 'Click "Sign In" in the top right corner, then select "Sign in with Google". You\'ll be redirected to Google\'s secure login page. Once authenticated, you\'ll be automatically signed up with the Free tier, which includes 20 pages per month.'
  },
  {
    id: 'getting-started-2',
    category: FAQCategory.GETTING_STARTED,
    question: 'How do I upload my first document?',
    answer: 'After signing in, go to the Dashboard and click "Upload Document" or drag and drop a PDF file directly onto the upload area. The AI will automatically process and categorize your document within seconds.'
  },
  {
    id: 'getting-started-3',
    category: FAQCategory.GETTING_STARTED,
    question: 'How does AI auto-categorization work?',
    answer: 'Our AI analyzes the content of your document using advanced natural language processing (NLP) and machine learning. It identifies document types (invoice, contract, receipt, etc.) and assigns them to the appropriate category automatically. The AI achieves 99% accuracy and continuously improves with usage.'
  },
  {
    id: 'getting-started-4',
    category: FAQCategory.GETTING_STARTED,
    question: 'What file formats are supported?',
    answer: 'Currently, Bonifatus DMS supports PDF files. We\'re working on adding support for DOCX, JPG, PNG, and other common document formats in future updates.'
  },
  {
    id: 'getting-started-5',
    category: FAQCategory.GETTING_STARTED,
    question: 'How does the document search work?',
    answer: 'Our smart search feature uses AI-powered OCR (Optical Character Recognition) to extract text from your documents, including scanned documents and handwritten notes. You can search by filename, content, date, category, or any text within the document. Results appear instantly as you type.'
  },
  {
    id: 'getting-started-6',
    category: FAQCategory.GETTING_STARTED,
    question: 'What languages are supported?',
    answer: 'Bonifatus DMS supports documents in <strong>English, German, Russian, French, Spanish, Italian, Portuguese, Dutch, Polish, Turkish, and many more languages</strong>. The AI automatically detects the document language and processes it accordingly. The user interface is currently available in English, German, and Russian, with more languages coming soon.'
  },
  {
    id: 'getting-started-7',
    category: FAQCategory.GETTING_STARTED,
    question: 'Can I process multilingual documents?',
    answer: 'Yes! The AI can analyze documents in multiple languages simultaneously. For example, if you have invoices in German and contracts in English, the system will process both correctly without any manual configuration.'
  },
  {
    id: 'getting-started-8',
    category: FAQCategory.GETTING_STARTED,
    question: 'How do categories work?',
    answer: 'Categories are folders that organize your documents automatically. The system comes with default categories like "Invoices", "Contracts", "Receipts", "Taxes", and "Personal". You can create custom categories, rename existing ones, or let the AI suggest new categories based on your document types.'
  },
  {
    id: 'getting-started-9',
    category: FAQCategory.GETTING_STARTED,
    question: 'Can I manually change a document\'s category?',
    answer: 'Absolutely! While the AI is 99% accurate, you can always manually move documents between categories. Simply click on a document, select "Change Category", and choose the correct one. The AI learns from your corrections and improves over time.'
  },
  {
    id: 'getting-started-10',
    category: FAQCategory.GETTING_STARTED,
    question: 'What is the difference between the Free, Starter, and Pro tiers?',
    answer: 'The <strong>Free tier</strong> includes 20 pages/month, perfect for trying out the service. The <strong>Starter tier</strong> offers 100 pages/month with bulk upload and email-to-process capabilities. The <strong>Pro tier</strong> provides unlimited pages, up to 10 team members, bulk processing, email-to-process feature, folder watching, and multi-cloud support (Google Drive, Dropbox, OneDrive, Box).'
  },
  {
    id: 'getting-started-11',
    category: FAQCategory.GETTING_STARTED,
    question: 'What counts as a "page"?',
    answer: 'A "page" is a single page within a PDF document. For example, a 5-page invoice counts as 5 pages toward your monthly limit. Only successfully processed pages count toward your quota.'
  },
  {
    id: 'getting-started-12',
    category: FAQCategory.GETTING_STARTED,
    question: 'Can I bulk upload documents?',
    answer: 'Yes! With the Starter or Pro tier, you can upload multiple documents at once (up to 50 files simultaneously on Pro). Simply drag and drop multiple PDFs, and the AI will process them all in the background. You\'ll receive a notification when processing is complete.'
  },
  {
    id: 'getting-started-13',
    category: FAQCategory.GETTING_STARTED,
    question: 'What is the email-to-process feature?',
    answer: 'Pro tier users get a unique email address (e.g., yourname@docs.bonidoc.com). Forward any document to this email, and it will be automatically processed, categorized, and added to your account. This is perfect for processing receipts, invoices, or documents received via email without logging into the dashboard.'
  },
  {
    id: 'getting-started-14',
    category: FAQCategory.GETTING_STARTED,
    question: 'How fast is document processing?',
    answer: 'Most documents are processed in 2-5 seconds. Larger documents (50+ pages) may take up to 30 seconds. Bulk uploads are processed in parallel, so uploading 100 documents typically completes within 2-3 minutes on the Pro tier.'
  },
  {
    id: 'getting-started-15',
    category: FAQCategory.GETTING_STARTED,
    question: 'Can I access my documents from multiple devices?',
    answer: 'Yes! Bonifatus DMS is a cloud-based system. Log in from any device (computer, tablet, phone) with your Google account, and you\'ll have instant access to all your documents. Your documents are synced in real-time across all devices.'
  },
  {
    id: 'getting-started-16',
    category: FAQCategory.GETTING_STARTED,
    question: 'Is there a mobile app?',
    answer: 'Currently, Bonifatus DMS is accessible via web browser on mobile devices. We\'re developing dedicated iOS and Android apps with enhanced mobile features, including camera document capture and offline access. Sign up for our newsletter to be notified when they launch.'
  },
  {
    id: 'getting-started-17',
    category: FAQCategory.GETTING_STARTED,
    question: 'Can I download my documents?',
    answer: 'Yes! You can download individual documents or entire categories as a ZIP file. Simply select the documents you want, click "Download", and they\'ll be saved to your device. Your original PDFs are preserved exactly as uploaded.'
  },
  {
    id: 'getting-started-18',
    category: FAQCategory.GETTING_STARTED,
    question: 'What happens if I exceed my monthly page limit?',
    answer: 'If you approach your page limit, we\'ll send you a notification. Once you reach the limit, document processing will be paused until the next billing cycle or you can upgrade your tier immediately. Already processed documents remain accessible, and you can still download, search, and view them.'
  },

  // ========================================
  // BILLING & SECURITY (14 questions)
  // ========================================
  {
    id: 'billing-1',
    category: FAQCategory.BILLING_SECURITY,
    question: 'How much does Bonifatus DMS cost?',
    answer: 'We offer three tiers: <strong>Free</strong> (€0/month, 20 pages/month), <strong>Starter</strong> (from €2.99/month or €28.70/year, 100 pages/month), and <strong>Pro</strong> (from €7.99/month or €76.70/year, unlimited pages, up to 10 team members). Annual billing saves you approximately 20%. Prices shown in EUR — other currencies are available at checkout.'
  },
  {
    id: 'billing-2',
    category: FAQCategory.BILLING_SECURITY,
    question: 'What payment methods do you accept?',
    answer: 'We accept all major credit cards (Visa, Mastercard, American Express), debit cards, and PayPal. Payments are processed securely through Stripe, a PCI-compliant payment processor. We do not store your payment information on our servers.'
  },
  {
    id: 'billing-3',
    category: FAQCategory.BILLING_SECURITY,
    question: 'When am I charged?',
    answer: 'For monthly subscriptions, you\'re charged on the same day each month as your initial subscription. For annual subscriptions, you\'re charged once per year on your subscription anniversary. You\'ll receive an email receipt for each charge.'
  },
  {
    id: 'billing-4',
    category: FAQCategory.BILLING_SECURITY,
    question: 'Can I upgrade or downgrade my tier anytime?',
    answer: 'Yes! You can <strong>upgrade immediately</strong>, and the change takes effect right away. When upgrading, you\'ll only pay the <strong>price difference</strong> between your current and new tier, prorated for the remaining time in your billing cycle. For example, if you\'re halfway through a Starter yearly subscription and upgrade to Pro, you\'ll pay roughly half of the Pro-Starter price difference. Your subscription continues with the same billing date. Downgrades take effect at your next billing cycle, and you keep current benefits until then.'
  },
  {
    id: 'billing-5',
    category: FAQCategory.BILLING_SECURITY,
    question: 'How do I cancel my subscription?',
    answer: 'Go to Settings > Billing, and click "Cancel Subscription". Your subscription will remain active until the end of your current billing cycle. After cancellation, you\'ll be downgraded to the Free tier, and you can still access and download all your documents.'
  },
  {
    id: 'billing-6',
    category: FAQCategory.BILLING_SECURITY,
    question: 'Is my data secure?',
    answer: 'Absolutely! <strong>Your documents are stored securely in YOUR own cloud storage</strong> (Google Drive, Dropbox, etc.), not on our servers. We only process documents temporarily during AI analysis and never permanently store them. All data transmission is encrypted using industry-standard TLS/SSL. We are GDPR compliant.'
  },
  {
    id: 'billing-7',
    category: FAQCategory.BILLING_SECURITY,
    question: 'Is Bonifatus DMS GDPR compliant?',
    answer: 'Yes! We are fully GDPR compliant. Your documents remain in your own cloud storage (within your chosen region), and we process data only as necessary to provide the service. You have full control over your data: view, download, or delete it anytime. We do not sell or share your personal information with third parties.'
  },
  {
    id: 'billing-8',
    category: FAQCategory.BILLING_SECURITY,
    question: 'Where are my documents stored?',
    answer: '<strong>Your documents are stored in YOUR personal cloud storage</strong> (Google Drive, Dropbox, OneDrive, or Box depending on your tier). We never store your documents on our servers. This means you have complete control and ownership of your data, and you can access your files directly through your cloud provider at any time.'
  },
  {
    id: 'billing-9',
    category: FAQCategory.BILLING_SECURITY,
    question: 'Can you access my documents?',
    answer: 'No. Your documents are stored in your own cloud storage, and we only access them temporarily during processing (with your explicit permission via OAuth). Our system processes documents, extracts metadata, and then immediately discards the temporary copy. We cannot view your documents unless you explicitly share them with our support team for troubleshooting.'
  },
  {
    id: 'billing-10',
    category: FAQCategory.BILLING_SECURITY,
    question: 'What encryption do you use?',
    answer: 'All data transmission between your browser and our servers is encrypted using TLS 1.3 (Transport Layer Security). Documents stored in your cloud are protected by your cloud provider\'s encryption (Google Drive, Dropbox, OneDrive all use AES-256 encryption at rest). API keys and access tokens are encrypted in our database using industry-standard encryption.'
  },
  {
    id: 'billing-11',
    category: FAQCategory.BILLING_SECURITY,
    question: 'Do you offer refunds?',
    answer: 'We offer a 14-day money-back guarantee for new subscriptions. If you\'re not satisfied within the first 14 days, contact our support team for a full refund. After 14 days, subscriptions are non-refundable, but you can cancel anytime to prevent future charges.'
  },
  {
    id: 'billing-12',
    category: FAQCategory.BILLING_SECURITY,
    question: 'Is there a free trial for paid tiers?',
    answer: 'All new users start with the Free tier (20 pages/month), which serves as a trial. You can test all core features including AI categorization and smart search before upgrading. There\'s no credit card required for the Free tier.'
  },
  {
    id: 'billing-13',
    category: FAQCategory.BILLING_SECURITY,
    question: 'What happens to my documents if I cancel?',
    answer: 'Your documents remain safely stored in YOUR cloud storage (Google Drive, etc.) and are not deleted. However, you\'ll lose access to Bonifatus DMS features like AI categorization and smart search. You can still access all your files directly through your cloud provider. If you resubscribe later, all your data and categories will be restored.'
  },
  {
    id: 'billing-14',
    category: FAQCategory.BILLING_SECURITY,
    question: 'Can I get an invoice for my subscription?',
    answer: 'Yes! An invoice is automatically emailed to you after each payment. You can also download invoices anytime from Settings > Billing > Invoice History. Invoices include all necessary details for business expense reporting and tax purposes.'
  },

  // ========================================
  // INTEGRATIONS & CLOUD STORAGE (11 questions)
  // ========================================
  {
    id: 'integrations-1',
    category: FAQCategory.INTEGRATIONS,
    question: 'How do I connect Google Drive?',
    answer: 'After signing up, go to Settings > Integrations and click "Connect Google Drive". You\'ll be redirected to Google\'s authorization page. Grant Bonifatus DMS permission to access your Drive, and we\'ll create a "Bonifatus DMS" folder where all your processed documents will be stored.'
  },
  {
    id: 'integrations-2',
    category: FAQCategory.INTEGRATIONS,
    question: 'Which cloud storage providers are supported?',
    answer: '<strong>Free and Starter tiers:</strong> Google Drive only. <strong>Pro tier:</strong> Google Drive, Dropbox, Microsoft OneDrive, and Box. You can connect multiple cloud accounts and switch between them anytime.'
  },
  {
    id: 'integrations-3',
    category: FAQCategory.INTEGRATIONS,
    question: 'Can I use my own cloud storage?',
    answer: 'Yes! That\'s the core principle of Bonifatus DMS. Your documents are stored in YOUR cloud storage account (Google Drive, Dropbox, OneDrive, or Box), not on our servers. You maintain full ownership and control of your files at all times.'
  },
  {
    id: 'integrations-4',
    category: FAQCategory.INTEGRATIONS,
    question: 'How do I switch between different cloud storage providers?',
    answer: 'Pro tier users can connect multiple cloud storage providers. Go to Settings > Integrations, connect your desired cloud accounts, then select which one should be your "Active Storage" from the dropdown menu. All new documents will be saved to the active storage. Existing documents remain in their original locations.'
  },
  {
    id: 'integrations-5',
    category: FAQCategory.INTEGRATIONS,
    question: 'Can I migrate my documents between cloud providers?',
    answer: 'Yes! Pro tier users can migrate documents between connected cloud storage providers. Go to Settings > Integrations > Migration Tool, select the source and destination providers, and choose which categories or documents to migrate. The migration process preserves all metadata, categories, and organization.'
  },
  {
    id: 'integrations-6',
    category: FAQCategory.INTEGRATIONS,
    question: 'How do I disconnect a cloud storage provider?',
    answer: 'Go to Settings > Integrations, find the connected provider, and click "Disconnect". <strong>Important:</strong> Your documents will remain in that cloud storage, but Bonifatus DMS will no longer have access to them. Make sure to download any documents you need before disconnecting.'
  },
  {
    id: 'integrations-7',
    category: FAQCategory.INTEGRATIONS,
    question: 'What permissions does Bonifatus DMS need from my cloud storage?',
    answer: 'We request minimal permissions: <strong>Read and Write access to the "Bonifatus DMS" folder only</strong>. We do NOT have access to your entire cloud storage, personal files, or any folders outside the Bonifatus DMS folder. You can revoke these permissions anytime from your cloud provider\'s security settings.'
  },
  {
    id: 'integrations-8',
    category: FAQCategory.INTEGRATIONS,
    question: 'Will connecting Bonifatus DMS affect my existing cloud storage files?',
    answer: 'No. Bonifatus DMS only creates and accesses files within a dedicated "Bonifatus DMS" folder in your cloud storage. Your existing files, folders, and documents remain completely untouched and inaccessible to our system.'
  },
  {
    id: 'integrations-9',
    category: FAQCategory.INTEGRATIONS,
    question: 'What are the storage quotas for each tier?',
    answer: '<strong>Free:</strong> 50 MB upload limit per month. <strong>Starter:</strong> 100 MB upload limit per month. <strong>Pro:</strong> 10 GB upload limit per month. Storage limits refer to the monthly upload volume within Bonifatus DMS. Your cloud provider\'s own storage quota also applies.'
  },
  {
    id: 'integrations-10',
    category: FAQCategory.INTEGRATIONS,
    question: 'Can I access my documents directly from my cloud provider?',
    answer: 'Absolutely! Since your documents are stored in YOUR cloud (Google Drive, etc.), you can access them anytime using your cloud provider\'s interface or mobile apps. Documents are organized in the "Bonifatus DMS" folder with category subfolders.'
  },
  {
    id: 'integrations-11',
    category: FAQCategory.INTEGRATIONS,
    question: 'What happens if I run out of cloud storage space?',
    answer: 'Document uploads will fail if your cloud storage is full. You\'ll need to either free up space in your cloud or upgrade your cloud storage plan. Bonifatus DMS will notify you when you\'re approaching your cloud storage limit.'
  },

  // ========================================
  // TROUBLESHOOTING & SUPPORT (8 questions)
  // ========================================
  {
    id: 'troubleshooting-1',
    category: FAQCategory.TROUBLESHOOTING,
    question: 'My document upload failed. What should I do?',
    answer: 'Common causes: 1) File is not a PDF (convert it first), 2) File is corrupted or password-protected, 3) File exceeds size limit (Free: 10MB, Starter: 50MB, Pro: 200MB per file), or 4) Your cloud storage is full. Check the error message for specific details. If the issue persists, contact support with the document filename.'
  },
  {
    id: 'troubleshooting-2',
    category: FAQCategory.TROUBLESHOOTING,
    question: 'The AI categorized my document incorrectly. How do I fix it?',
    answer: 'Simply click on the document, select "Change Category", and choose the correct category. The AI learns from your corrections and will improve accuracy for similar documents in the future. If you notice repeated categorization errors for a specific document type, contact support so we can fine-tune the AI.'
  },
  {
    id: 'troubleshooting-3',
    category: FAQCategory.TROUBLESHOOTING,
    question: 'How do I reset all my categories?',
    answer: 'Go to Settings > Categories > Advanced Options, then click "Reset to Default Categories". <strong>Warning:</strong> This will delete all custom categories and reassign documents to default categories (Invoices, Contracts, Receipts, etc.). The AI will re-categorize documents automatically. Your documents themselves are not deleted.'
  },
  {
    id: 'troubleshooting-4',
    category: FAQCategory.TROUBLESHOOTING,
    question: 'I can\'t log in. What should I do?',
    answer: 'Bonifatus DMS uses Google Sign-In for authentication. Make sure: 1) You\'re using the same Google account you signed up with, 2) Pop-ups are not blocked in your browser, and 3) Third-party cookies are enabled. If issues persist, try clearing your browser cache or using an incognito/private window. Still having trouble? Contact support.'
  },
  {
    id: 'troubleshooting-5',
    category: FAQCategory.TROUBLESHOOTING,
    question: 'My email-to-process isn\'t working (Pro tier)',
    answer: 'Check: 1) You\'re sending from the email address registered with your account, 2) The document is attached as a PDF, 3) The email was sent to the correct address (yourname@docs.bonidoc.com - find it in Settings > Email Processing), and 4) The attachment size is under 100MB. Processing can take up to 5 minutes. Check your spam folder for confirmation emails.'
  },
  {
    id: 'troubleshooting-6',
    category: FAQCategory.TROUBLESHOOTING,
    question: 'The search isn\'t finding my document. Why?',
    answer: 'Possible reasons: 1) The document is still being processed (wait 30 seconds and try again), 2) The document is scanned and OCR extraction failed (try re-uploading a higher-quality scan), 3) The search term is misspelled, or 4) The document is in a category you\'ve filtered out. Try searching with different keywords or use "All Categories" filter.'
  },
  {
    id: 'troubleshooting-7',
    category: FAQCategory.TROUBLESHOOTING,
    question: 'How do I contact support?',
    answer: 'Email us at <a href="mailto:support@bonidoc.com" class="text-admin-primary hover:underline">support@bonidoc.com</a> or use the "Contact Support" button in Settings. Free tier: response within 48 hours. Starter tier: response within 24 hours. Pro tier: priority support with response within 12 hours (business days). Include your account email and a detailed description of the issue.'
  },
  {
    id: 'troubleshooting-8',
    category: FAQCategory.TROUBLESHOOTING,
    question: 'Can I request new features?',
    answer: 'Absolutely! We love hearing from our users. Submit feature requests via email to <a href="mailto:feedback@bonidoc.com" class="text-admin-primary hover:underline">feedback@bonidoc.com</a> or through the feedback form in Settings. Pro tier users have priority for feature requests, and we review all suggestions during our monthly product roadmap meetings.'
  },
]

// Helper to get FAQs by category
export function getFAQsByCategory(category: FAQCategory): FAQ[] {
  return faqs.filter(faq => faq.category === category)
}

// Helper to get all unique categories
export function getCategories(): string[] {
  return Object.values(FAQCategory)
}

// Helper to search FAQs
export function searchFAQs(query: string): FAQ[] {
  const lowerQuery = query.toLowerCase()
  return faqs.filter(
    faq =>
      faq.question.toLowerCase().includes(lowerQuery) ||
      faq.answer.toLowerCase().includes(lowerQuery)
  )
}
