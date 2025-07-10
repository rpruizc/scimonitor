import { Layout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { 
  Github, 
  Twitter, 
  Mail, 
  ExternalLink, 
  FileText, 
  MessageSquare,
  TrendingUp,
  Search
} from 'lucide-react';

export default function AboutPage() {
  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">About DLMonitor</h1>
          <p className="text-muted-foreground">
            Your comprehensive platform for monitoring deep learning research
          </p>
        </div>

        {/* Main Content */}
        <div className="grid gap-6 md:grid-cols-3">
          <div className="md:col-span-2 space-y-6">
            {/* Overview */}
            <Card>
              <CardHeader>
                <CardTitle>What is DLMonitor?</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm leading-relaxed">
                  DLMonitor is a comprehensive platform designed to help researchers, practitioners, and enthusiasts 
                  stay up-to-date with the rapidly evolving field of deep learning. We aggregate content from 
                  multiple sources including arXiv papers, Twitter discussions, and academic publications to provide 
                  a centralized hub for deep learning research.
                </p>
                <p className="text-sm leading-relaxed">
                  Our mission is to make deep learning research more accessible and discoverable by providing 
                  advanced search capabilities, trend analysis, and community discussions all in one place.
                </p>
              </CardContent>
            </Card>

            {/* Features */}
            <Card>
              <CardHeader>
                <CardTitle>Key Features</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <FileText className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <h4 className="font-medium">Paper Aggregation</h4>
                        <p className="text-sm text-muted-foreground">
                          Automatic collection from arXiv and other sources
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <MessageSquare className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <h4 className="font-medium">Social Monitoring</h4>
                        <p className="text-sm text-muted-foreground">
                          Track discussions on Twitter and other platforms
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <Search className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <h4 className="font-medium">Advanced Search</h4>
                        <p className="text-sm text-muted-foreground">
                          Powerful search across papers and discussions
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <TrendingUp className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <h4 className="font-medium">Trend Analysis</h4>
                        <p className="text-sm text-muted-foreground">
                          Identify emerging topics and trends
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Technology Stack */}
            <Card>
              <CardHeader>
                <CardTitle>Technology Stack</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-2">Frontend</h4>
                    <div className="flex gap-2 flex-wrap">
                      <Badge variant="secondary">Next.js 14</Badge>
                      <Badge variant="secondary">TypeScript</Badge>
                      <Badge variant="secondary">Tailwind CSS</Badge>
                      <Badge variant="secondary">shadcn/ui</Badge>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-medium mb-2">Backend</h4>
                    <div className="flex gap-2 flex-wrap">
                      <Badge variant="secondary">FastAPI</Badge>
                      <Badge variant="secondary">Python</Badge>
                      <Badge variant="secondary">PostgreSQL</Badge>
                      <Badge variant="secondary">Redis</Badge>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-medium mb-2">Data Sources</h4>
                    <div className="flex gap-2 flex-wrap">
                      <Badge variant="outline">arXiv API</Badge>
                      <Badge variant="outline">Twitter API</Badge>
                      <Badge variant="outline">Academic APIs</Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Platform Statistics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Papers Indexed</span>
                  <span className="font-semibold">1.2M+</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Daily Updates</span>
                  <span className="font-semibold">500+</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Categories</span>
                  <span className="font-semibold">25+</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Active Users</span>
                  <span className="font-semibold">10K+</span>
                </div>
              </CardContent>
            </Card>

            {/* Contact */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Contact & Links</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button variant="outline" className="w-full justify-start">
                  <Github className="h-4 w-4 mr-2" />
                  GitHub Repository
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Twitter className="h-4 w-4 mr-2" />
                  Follow on Twitter
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Mail className="h-4 w-4 mr-2" />
                  Contact Support
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Documentation
                </Button>
              </CardContent>
            </Card>

            {/* Version */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Version Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Version</span>
                    <span className="font-mono">v2.1.0</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Updated</span>
                    <span>Dec 2024</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">License</span>
                    <span>MIT</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
} 