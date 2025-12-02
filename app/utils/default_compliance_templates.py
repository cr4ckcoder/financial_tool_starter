# app/utils/default_compliance_templates.py

DEFAULT_TEMPLATES = [
    {
        "name": "1.1 Letter Seeking Auditor's Consent",
        "content": """
        <h3>LETTER SEEKING AUDITOR'S CONSENT</h3>
        <p><strong>Date:</strong> {{assignment.date}}</p>
        <p><strong>To,</strong><br>
        {{cafirm.name}}<br>
        {{cafirm.address}}</p>
        <p><strong>Subject: Seeking Consent and Eligibility letter for appointment as statutory auditors.</strong></p>
        <p>Dear Sirs,</p>
        <p>The Board of Directors of <strong>{{client.company.name}}</strong> in the forthcoming Meeting may consider appointment/reappointment of Statutory Auditors as required under Section 139 of the Companies Act, 2013 for the financial year {{assignment.financialyear}}.</p>
        <p>We would request you to please convey your willingness and eligibility to be appointed as the Statutory Auditor of the Company. We also request you to provide the certificate required u/s 141 of the Companies Act, 2013.</p>
        <br>
        <p>For <strong>{{client.company.name}}</strong></p>
        <br><br>
        <p><strong>Director / Authorized Signatory</strong></p>
        """
    },
    {
        "name": "1.2 Auditor's Consent & Certificate",
        "content": """
        <h3>CONSENT AND CERTIFICATE</h3>
        <p><strong>To,</strong><br>
        The Board of Directors,<br>
        {{client.company.name}}<br>
        {{client.company.address}}</p>
        <p><strong>Sub: Consent for Appointment as Auditor and Certificate of Eligibility</strong></p>
        <p>Dear Sirs,</p>
        <p>We, <strong>{{cafirm.name}}</strong>, Chartered Accountants, hereby give our consent to be appointed as Auditor of your Company u/s 139(1) of the Companies Act, 2013.</p>
        <p>We certify that we satisfy the conditions provided in section 141 of Companies Act, 2013.</p>
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
            <tr><td width="40%">Name of Firm</td><td><strong>{{cafirm.name}}</strong></td></tr>
            <tr><td>FRN</td><td>{{cafirm.frn}}</td></tr>
            <tr><td>Address</td><td>{{cafirm.address}}</td></tr>
            <tr><td>PAN</td><td>{{cafirm.pan}}</td></tr>
        </table>
        <br>
        <p>For <strong>{{cafirm.name}}</strong><br>Chartered Accountants</p>
        <p>Partner</p>
        """
    },
    {
        "name": "1.3 NOC from Previous Auditor",
        "content": """
        <h3>NO OBJECTION CERTIFICATE</h3>
        <p><strong>To,</strong><br>
        {{cafirm.name}}<br>
        Chartered Accountants</p>
        <p><strong>Sub: NOC for appointment as Statutory Auditor of {{client.company.name}}</strong></p>
        <p>Dear Sir,</p>
        <p>This is to certify that we have no objection to <strong>{{cafirm.name}}</strong> accepting the appointment as statutory auditor of <strong>{{client.company.name}}</strong>.</p>
        <p>We confirm that we have no outstanding dues from the company and have relinquished all claims regarding this audit assignment.</p>
        <br>
        <p>Yours faithfully,</p>
        <p><strong>(Previous Auditor)</strong></p>
        """
    },
    {
        "name": "1.4 Appointment Letter",
        "content": """
        <h3>APPOINTMENT LETTER</h3>
        <p><strong>To,</strong><br>
        {{cafirm.name}}<br>
        Chartered Accountants</p>
        <p><strong>Sub: Appointment as Statutory Auditors</strong></p>
        <p>Dear Sirs,</p>
        <p>We are pleased to inform you that your firm <strong>{{cafirm.name}}</strong> (FRN: {{cafirm.frn}}) is appointed as Statutory Auditors of <strong>{{client.company.name}}</strong> for the financial year {{assignment.financialyear}} to hold office up to the ensuing Annual General Meeting.</p>
        <p>You are requested to confirm your acceptance.</p>
        <br>
        <p>By order of the Board of Directors of<br>
        <strong>{{client.company.name}}</strong></p>
        """
    },
    {
        "name": "1.5 Engagement Letter",
        "content": """
        <h3>ENGAGEMENT LETTER</h3>
        <p><strong>To,</strong><br>
        The Board of Directors<br>
        {{client.company.name}}</p>
        <p>Dear Sirs,</p>
        <p>We refer to your letter informing us about our appointment as auditors of the Company. We are pleased to confirm our acceptance and our understanding of this audit engagement by means of this letter.</p>
        <p>Our audit will be conducted with the objective of expressing an opinion on the financial statements for the year ended <strong>{{assignment.end_date}}</strong>.</p>
        <p>We look forward to full cooperation from your staff during our audit.</p>
        <br>
        <p>For <strong>{{cafirm.name}}</strong><br>Chartered Accountants</p>
        """
    },
    {
        "name": "2.1 Independent Auditor's Report",
        "content": """
        <h3>INDEPENDENT AUDITOR'S REPORT</h3>
        <p><strong>To the Members of {{client.company.name}}</strong></p>
        <h4>Report on the Audit of the Financial Statements</h4>
        <p><strong>Opinion</strong></p>
        <p>We have audited the financial statements of <strong>{{client.company.name}}</strong> ("the Company"), which comprise the Balance Sheet as at <strong>{{assignment.end_date}}</strong>, the Statement of Profit and Loss, and the Cash Flow Statement for the year then ended.</p>
        <p>In our opinion, the aforesaid financial statements give the information required by the Act in the manner so required and give a true and fair view in conformity with the accounting principles generally accepted in India.</p>
        <br>
        <p>For <strong>{{cafirm.name}}</strong><br>Chartered Accountants<br>FRN: {{cafirm.frn}}</p>
        """
    },
    {
        "name": "2.4 Management Representation Letter",
        "content": """
        <h3>MANAGEMENT REPRESENTATION LETTER</h3>
        <p><strong>To,</strong><br>
        {{cafirm.name}}<br>
        Chartered Accountants</p>
        <p>Dear Sirs,</p>
        <p>This representation letter is provided in connection with your audit of the financial statements of <strong>{{client.company.name}}</strong> for the year ended <strong>{{assignment.end_date}}</strong>.</p>
        <p>We acknowledge our responsibility for the preparation of financial statements in accordance with the accounting principles generally accepted in India. We confirm that:</p>
        <ul>
            <li>We have made available to you all books of account and supporting documentation.</li>
            <li>There have been no irregularities involving management or employees who have a significant role in internal control.</li>
            <li>The company has complied with all aspects of contractual agreements that could have a material effect on the financial statements in the event of non-compliance.</li>
        </ul>
        <br>
        <p>For <strong>{{client.company.name}}</strong></p>
        <br>
        <p><strong>Director</strong></p>
        """
    }
]