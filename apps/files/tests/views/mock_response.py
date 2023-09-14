class MockResponse:
    def __init__(self):
        self.status_code = 200
        self.title = "Bankers hate him!!! This guy discovered a simple trick to become rich quickly!"
        self.description = (
            "Discover our top 10 tricks to become a billionaire in just a few days !"
        )
        self.image = "https://as1.ftcdn.net/v2/jpg/01/13/96/70/1000_F_113967069_We6GnlQl7icXaoKIVreKLpZIM4xSQEwn.jpg"
        self.site_name = "Super clickbait"
        self.text = """
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <meta content="{}" property="og:title"/>
                    <meta content="{}" property="og:description"/>
                    <meta content="{}" property="og:image"/>
                    <meta content="{}" property="og:site_name"/>
                    <title>Super clickbait</title>
                </head>
                <body>
                    <h1>Discover our top 10 tricks to become a billionaire in just a few days !</h1>
                    <ol>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                        <li>Inherit a shit-ton of money</li>
                    </ol>
                </body>
            </html>
            """.format(
            self.title, self.description, self.image, self.site_name
        )
