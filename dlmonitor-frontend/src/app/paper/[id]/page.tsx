import { Layout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { 
  ExternalLink, 
  Download, 
  Share, 
  BookmarkPlus, 
  Calendar, 
  Users,
  MessageSquare,
  TrendingUp 
} from 'lucide-react';

export default async function PaperDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // TODO: Use id to fetch paper data from API
  
  return (
    <Layout>
      <div className="space-y-6">
        {/* Back Button */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm">
            ← Back to Search
          </Button>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <BookmarkPlus className="h-4 w-4 mr-2" />
              Save
            </Button>
            <Button variant="outline" size="sm">
              <Share className="h-4 w-4 mr-2" />
              Share
            </Button>
          </div>
        </div>

        {/* Paper Header */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="secondary">arXiv</Badge>
              <Badge variant="outline">Computer Vision</Badge>
              <Badge variant="outline">Machine Learning</Badge>
            </div>
            <CardTitle className="text-2xl">
              Attention Is All You Need: Transformer Networks for Sequence-to-Sequence Learning
            </CardTitle>
            <CardDescription className="text-base">
              We propose a new simple network architecture, the Transformer, based solely on attention mechanisms,
              dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks
              show these models to be superior in quality while being more parallelizable.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">
                    <strong>Authors:</strong> Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">
                    <strong>Published:</strong> June 12, 2017
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <ExternalLink className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">
                    <strong>arXiv ID:</strong> 1706.03762
                  </span>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <Button className="w-full">
                  <Download className="h-4 w-4 mr-2" />
                  Download PDF
                </Button>
                <Button variant="outline" className="w-full">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View on arXiv
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-3">
          {/* Abstract */}
          <div className="md:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Abstract</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed">
                  The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature.
                </p>
              </CardContent>
            </Card>

            {/* Key Contributions */}
            <Card>
              <CardHeader>
                <CardTitle>Key Contributions</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                    <span>Introduced the Transformer architecture based solely on attention mechanisms</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                    <span>Eliminated recurrence and convolutions for improved parallelization</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                    <span>Achieved state-of-the-art results on machine translation tasks</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                    <span>Demonstrated superior quality while requiring less training time</span>
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Metrics */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Citations</span>
                  <span className="font-semibold">89,234</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Downloads</span>
                  <span className="font-semibold">1.2M</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Impact Score</span>
                  <span className="font-semibold">9.8</span>
                </div>
                <Separator />
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Trending</span>
                  <TrendingUp className="h-4 w-4 text-green-500" />
                </div>
              </CardContent>
            </Card>

            {/* Related Discussions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Discussions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="space-y-1">
                    <p className="text-sm font-medium">
                      Discussion about attention mechanisms
                    </p>
                    <p className="text-xs text-muted-foreground">
                      @researcher • 2 hours ago
                    </p>
                  </div>
                ))}
                <Button variant="outline" size="sm" className="w-full">
                  View All Discussions
                </Button>
              </CardContent>
            </Card>

            {/* Related Papers */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Related Papers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="space-y-1">
                    <p className="text-sm font-medium leading-tight">
                      BERT: Pre-training of Deep Bidirectional Transformers
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Devlin et al. • 2018
                    </p>
                  </div>
                ))}
                <Button variant="outline" size="sm" className="w-full">
                  View All Related
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
} 