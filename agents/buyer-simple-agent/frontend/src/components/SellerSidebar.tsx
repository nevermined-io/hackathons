import { Store } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { Seller } from "@/api";

interface SellerSidebarProps {
  sellers: Seller[];
}

export default function SellerSidebar({ sellers }: SellerSidebarProps) {
  return (
    <div className="flex flex-col h-full bg-card border-r">
      <div className="flex items-center gap-2 px-4 py-3">
        <Store className="h-4 w-4 text-primary" />
        <span className="font-semibold text-sm">Sellers</span>
        {sellers.length > 0 && (
          <Badge className="ml-auto h-5 text-[10px]">{sellers.length}</Badge>
        )}
      </div>
      <Separator />
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-3">
          {sellers.length === 0 && (
            <div className="flex items-center gap-2 px-2 py-8 text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-primary animate-pulse-dot" />
              <span className="text-sm">Waiting for sellers...</span>
            </div>
          )}
          {sellers.map((seller) => (
            <Card key={seller.url} className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle className="text-sm">{seller.name}</CardTitle>
                {seller.description && (
                  <p className="text-xs text-muted-foreground leading-snug line-clamp-2">
                    {seller.description}
                  </p>
                )}
              </CardHeader>
              <CardContent className="p-3 pt-2 space-y-2">
                {seller.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {seller.skills.map((skill) => (
                      <Badge
                        key={skill}
                        variant="secondary"
                        className="text-[10px] bg-primary/10 text-primary border-0 font-medium"
                      >
                        {skill}
                      </Badge>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    {seller.cost_description || `${seller.credits} credit${seller.credits !== 1 ? "s" : ""}`}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
